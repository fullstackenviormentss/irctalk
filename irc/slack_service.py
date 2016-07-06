import logging
import os
import signal
import time
import traceback

import tornado.ioloop
import tornado.log

from irc.slack_client import SlackClient
from irc.talkback import Talkback


CONFIG = os.environ["SLACK_CONFIG"]
URI = os.environ["SLACK_URI"]


def main():
    tornado.log.enable_pretty_logging()
    ioloop = tornado.ioloop.IOLoop.instance()
    talkback = Talkback(ioloop=ioloop, config=CONFIG)
    client = SlackClient(URI, ioloop)
    talkback.register(client)
    future = client.listen()

    def callback(f):
        ioloop.stop()
        try:
            f.result()
        except Exception:
            logging.error(
                "Error in stream: {0}".format(traceback.format_exc()))

    future.add_done_callback(callback)

    def timeout():
        logging.info("Shutdown timed out -- killing.")
        ioloop.stop()

    def shutdown(_, __):
        logging.info("Stopping the Slack client...")
        client.stop()
        ioloop.add_timeout(time.time() + 2, timeout)

    signal.signal(signal.SIGINT, shutdown)

    ioloop.start()
    logging.info("Slack service is stopped.")


if __name__ == "__main__":
    main()
