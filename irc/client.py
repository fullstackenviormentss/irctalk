import logging
import socket

from tornado import gen
from tornado.iostream import IOStream, StreamClosedError

from irc.connection import IRCConnection
from irc.message import Message
from irc.callbacks import pong_callback, debug_callback, die_callback


class IRCClient(object):

    def __init__(self, uri, ioloop):
        self.ioloop = ioloop
        self.callbacks = {
            "PING": [pong_callback],
            "NOTICE": [debug_callback],
            "ERROR": [die_callback]
        }
        self.conn = IRCConnection.from_uri(uri)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(self.socket, io_loop=ioloop)
        self.current_chunk = ""

    def add_message_callback(self, command, func):
        self.callbacks.setdefault(command, []).append(func)

    def read_timeout(self):
        if self.message_future and not self.message_future.done():
            self.message_future.set_exception(ReadTimeout("TIMEOUT"))

    def stream_bytes(self, chunk):
        self.current_chunk += chunk
        while "\r\n" in self.current_chunk:
            original_message, self.current_chunk = self.current_chunk.split(
                "\r\n", 1)

            message = Message.from_message(original_message)

            if message.ident[1:].startswith(self.conn.username):
                logging.debug(
                    "Skipping message from self: {0}".format(message.message))
                continue

            if message.command not in self.callbacks:
                logging.info("SKIPPING - {0}".format(original_message))
                continue

            for callback in self.callbacks[message.command]:
                try:
                    callback(message, self.stream)
                except StreamClosedError:
                    logging.error("Stream was closed.")
                    raise
                except Exception as exc:
                    logging.error("Exception {0} in callback.".format(exc))

    @gen.coroutine
    def listen(self):
        logging.info(
            "Connecting to {0}:{1}".format(self.conn.host, self.conn.port))
        self.stream.connect((self.conn.host, self.conn.port))

        logging.info("Registering the client.")

        self.stream.write("PASS {0}\r\n".format(self.conn.password))
        self.stream.write("NICK {0}\r\n".format(self.conn.username))
        self.stream.write("USER {0} {1} unused :{2}\r\n".format(
            self.conn.username, socket.gethostname(), self.conn.name))
        for channel in self.conn.channels:
            logging.info("Joining channel: #{0}".format(channel))
            self.stream.write("JOIN #{0}\r\n".format(channel))

        try:
            yield self.stream.read_until_close(
                streaming_callback=self.stream_bytes)
        except StreamClosedError:
            logging.error("Stream is closed.")
            raise gen.Return(False)
        raise gen.Return(True)

    def stop(self):
        logging.info("Client no longer listening.")
        self.stream.write("QUIT\r\n")
        self.stream.close()


class ReadTimeout(Exception):
    pass
