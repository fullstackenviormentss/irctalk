import logging


def pong_callback(message, stream):
    servers = message.message
    logging.info("Responding to PING from {0}".format(servers))
    stream.write("PONG {0}\r\n".format(servers))


def debug_callback(message, stream):
    logging.info("DEBUG: {0} {1}".format(message.command, message.message))


def die_callback(message, stream):
    logging.error("ERROR: {0}".format(message.message))
    logging.info("Shutting down stream.")
    stream.close()
