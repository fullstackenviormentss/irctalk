class Message(object):

    def __init__(self, ident, command, message):
        self.ident = ident
        self.command = command
        self.message = message

    @classmethod
    def from_message(cls, message):
        ident, message = message.split(" ", 1)
        if not ident.startswith(":"):
            command = ident
            ident = ""
        elif " " in message:
            command, message = message.split(" ", 1)
        else:
            command = message
            message = ""
        return cls(ident, command, message)
