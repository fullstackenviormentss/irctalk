from __future__ import print_function
import logging
import os
import signal
import time

from tornado.ioloop import IOLoop
import tornado.log

from irc.client import IRCClient
from irc.talkback import Talkback


def main():
    uri = os.environ["IRC_URI"]
    config = os.environ["IRC_CONFIG"]
    tornado.log.enable_pretty_logging()
    loop = IOLoop().current()
    talkback = Talkback(ioloop=loop, config=config)
    client = IRCClient(uri, ioloop=loop)
    talkback.register(client)
    listen_future = client.listen()

    def callback(future):
        loop.stop()

    listen_future.add_done_callback(callback)

    def timeout():
        logging.info("Shutdown timed out -- killing.")
        loop.stop()

    def shutdown(_, __):
        logging.info("Stopping the client...")
        client.stop()
        loop.add_timeout(time.time() + 2, timeout)

    signal.signal(signal.SIGINT, shutdown)
    loop.start()
    logging.info("Client is closed.")


if __name__ == "__main__":
    main()
