import json
import logging
import random
import traceback

import tornado.gen
import tornado.ioloop
import tornado.httpclient
import tornado.websocket

from irc.message import Message


def message_transform(msg):
    text = msg["text"]
    channel = msg["channel"]
    user = msg["user"]
    irc_msg = u":{0} PRIVMSG #{1} {2}".format(user, channel, text)
    message = Message.from_message(irc_msg)
    return message


_IRC_TRANSFORMS = {
    "message": message_transform,
}


class SlackStream(object):

    def __init__(self, socket):
        self.socket = socket

    def write(self, message):
        message = message.decode("utf8")
        logging.info("Sending message: {0}".format(message))
        action, channel, text = message.split(" ", 2)
        # the message starts with a ':'
        self.socket.write_message(json.dumps({
            "id": random.randint(1, 1024 * 1024 * 512),
            "type": "message",
            "channel": channel[1:],
            "text": text[1:]
        }).encode("utf8"))


class SlackClient(object):

    def __init__(self, uri, ioloop):
        self.uri = uri
        self.ioloop = ioloop
        self.callbacks = {}

    @tornado.gen.coroutine
    def listen(self):
        logging.info("Connecting to Slack API...")
        response = yield self.authorize()
        wss_url = response["url"]
        self.socket_client = yield self.socket_connect(wss_url)
        self.stream = SlackStream(self.socket_client)
        yield self.monitor_stream()

    @tornado.gen.coroutine
    def authorize(self):
        client = tornado.httpclient.AsyncHTTPClient(io_loop=self.ioloop)
        body = {
            "simple_latest": "true",
            "no_unreads": "true"
        }
        response = yield client.fetch(
            self.uri, method="POST", body=json.dumps(body),
            headers={"Content-type": "application/json; charset=utf-8"})

        body = json.loads(response.body)

        if response.code != 200 or not body.get("ok"):
            raise Exception(
                "ERROR INITIALIZING {0}: \n{1}".format(
                    response.code, body["warning"]))

        raise tornado.gen.Return(body)

    @tornado.gen.coroutine
    def socket_connect(self, url):
        client = yield tornado.websocket.websocket_connect(
            url=url, io_loop=self.ioloop)
        raise tornado.gen.Return(client)

    @tornado.gen.coroutine
    def monitor_stream(self):
        while True:
            message = yield self.socket_client.read_message()
            if not message:
                raise Exception("Invalid / null message.")
            message = json.loads(message)

            logging.info("Parsing new message: {0}".format(message))

            if message.get("reply_to"):
                logging.info("Skipping a reply.")
                continue

            msg_type = message.get("type")
            if msg_type not in _IRC_TRANSFORMS:
                logging.warning("Unknown message type: {0}\n{1}".format(
                    msg_type, message))
                continue

            message = _IRC_TRANSFORMS[msg_type](message)
            if message.command not in self.callbacks:
                logging.warning(
                    "Skipping message: {0}".format(message.message))
                continue

            for callback in self.callbacks[message.command]:
                try:
                    callback(message, self.stream)
                except Exception:
                    logging.error(
                        "Error in callback: {0}".format(
                            traceback.format_exc()))

    def add_message_callback(self, command, func):
        self.callbacks.setdefault(command, []).append(func)

    def stop(self):
        if hasattr(self, "socket_client"):
            self.socket_client.close()
