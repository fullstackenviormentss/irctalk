import logging
import random
import re
import time
import yaml


class Talkback(object):

    def __init__(self, ioloop, config):
        self.ioloop = ioloop

        with open(config) as yaml_fp:
            self.config = yaml.load(yaml_fp)

        for command in self.config["commands"]:
            command.setdefault("regex", command["command"])
            command["regex"] = re.compile(command["regex"])

    def register(self, client):
        client.add_message_callback("PRIVMSG", self.parse_message)

    def parse_message(self, message, stream):
        channel, contents = message.message.split(" ", 1)
        if not channel.startswith("#"):
                username = message.ident[1:].split("!")[0]
                logging.info("Not a channel ({0}) -- using {1}".format(
                    channel, username))
                channel = username

        contents = contents.lower()

        for config in self.config["commands"]:
            match = config["regex"].search(contents)
            if not match:
                continue
            return self.run_command(config, channel, match.groups(), stream)

        logging.info("Ignoring message: {0}".format(contents))

    def run_command(self, config, channel, matches, stream):
        arg_type = config["type"]
        attr_name = "run_{0}_command".format(arg_type)
        attribute = getattr(self, attr_name, None)
        if not attribute:
            logging.info("Unknown arg type: {0}".format(arg_type))
            self.send_wtf(stream, channel, arg_type)
            return
        return attribute(config, channel, matches, stream)

    def run_announce_command(self, config, channel, matches, stream):
        prefixes = ["!", "#"]
        args = [m for m in matches if m and m[0] not in prefixes]
        channels = [m for m in matches if m and m[0] in prefixes]
        if len(channels) > 1:
            logging.info("Too many channels: {0}".format(matches))
            self.send(stream, channel, "Please provide a single #channel.")
            return
        elif len(channels) == 1:
            channel = channels[0].replace("!", "")
        else:
            logging.info("No channel provided, using: {0}".format(channel))
        announce_config = config["announce_config"]
        self.run_command(announce_config, channel, args, stream)

    def run_help_command(self, config, channel, matches, stream):
        for command in self.config["commands"]:
            if not command.get("show_help"):
                continue
            description = command.get("description", "no description")
            self.send(stream, channel, "{0} - {2}".format(
                command["command"], description))

    def run_random_command(self, config, channel, matches, stream):
        choices = get_list(config, "choices", self.config["parameters"])
        choice = random.choice(choices).format(*matches)
        self.send(stream, channel, choice)

    def run_sequence_command(self, config, channel, matches, stream):
        sequence = get_list(config, "sequence", self.config["parameters"])
        start_time = time.time()
        for offset, message in sequence:
            message = message.format(*matches)
            self.ioloop.add_timeout(
                start_time + offset, self.send, stream, channel, message)

    def run_say_command(self, config, channel, matches, stream):
        statement = config["message"].format(*matches)
        self.send(stream, channel, statement)

    def send_wtf(self, stream, channel, error):
        self.send(stream, channel, "No clue what '{0}' means.".format(error))

    def send(self, stream, channel, message):
        send_msg = u"PRIVMSG {0} :{1}\r\n".format(channel, message)
        stream.write(send_msg.encode("utf8"))


def get_list(config, key, parameters):
    items = config[key]
    if type(items) == dict and items["get_param"]:
        items = parameters[items["get_param"]]
    return items
