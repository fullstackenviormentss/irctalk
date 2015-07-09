import urlparse


class IRCConnection(object):

    def __init__(self, host, port, username, password, name, channels):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.name = name
        self.channels = channels
        self.message_future = None

    @classmethod
    def from_uri(cls, uri):
        parsed = urlparse.urlparse(uri)
        auth, host = parsed.netloc.split("@")
        host += ":6667" if ":" not in host else ""
        host, port = host.split(":")
        port = int(port)
        auth += ":" if ":" not in auth else ""
        username, password = auth.split(":", 1)
        query = dict(urlparse.parse_qsl(parsed.query))
        name = query.get("name", username)
        channels = [c for c in parsed.path[1:].split(",") if c]
        return cls(host, port, username, password, name, channels)
