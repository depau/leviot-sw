import sys

import micropython

from leviot import VERSION, ulog

_status_messages = {
    101: "Switching Protocols",
    200: "OK",
    303: "See Other",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    406: "Not Acceptable",
    500: "Internal Server Error",
}

log = ulog.Logger("uhttp")


class HTTPError(Exception):
    pass


class HTTPRequest:
    def __init__(self, method: str, path: str, query: dict, segment: str, headers: dict):
        self.method = method
        self.path = path
        self.query = query
        self.segment = segment
        self.headers = headers

    @micropython.native
    def check_basic_auth(self, basic_b64):
        return not ('authorization' not in self.headers or self.headers['authorization'] != basic_b64)

    @staticmethod
    @micropython.native
    def _parse_path(path: str):
        query, query_raw, segment = {}, None, None
        if '?' in path:
            path, query_raw = path.split("?", 1)
        if query_raw and '#' in query_raw:
            query_raw, segment = query_raw.split("#", 1)

        if query_raw:
            query = {key: val for key, val in
                     (item.split('=', 1) for item in query_raw.split("&"))}
        return path, query, segment

    @staticmethod
    @micropython.native
    def _parse_header(line: bytes):
        line = line.decode().strip()
        if not line:
            return False, None, None
        if ":" not in line:
            return True, None, None

        name, value = line.split(":", 1)
        return True, name.strip().lower(), value.strip()

    @classmethod
    async def parse(cls, reader) -> 'HTTPRequest':
        line = (await reader.readline()).decode().strip()
        if not line:
            raise HTTPError("Empty request")
        split = line.split(' ', 2)
        try:
            method = split[0]
            path = split[1]
        except IndexError as e:
            log.e("Invalid HTTP request string: " + line)
            raise HTTPError(str(e))

        path, query, segment = cls._parse_path(path)

        headers = {}
        proceed = True
        while proceed:
            line = await reader.readline()
            proceed, name, value = cls._parse_header(line)
            if name:
                headers[name] = value

        return cls(method, path, query, segment, headers)


class HTTPResponse:
    @micropython.native
    def __init__(self, status: int = 200, http_version="HTTP/1.1", headers=None, status_mesg=None, body=None):
        self.status = status
        self.http_version = http_version
        self.headers = headers if headers else {}
        self.status_mesg = status_mesg if status_mesg else _status_messages.get(status, None)
        self.body = body
        if not body and status >= 400 and self.status_mesg:
            self.body = "{} {}\n".format(status, self.status_mesg).encode()

        if 'Server' not in self.headers and 'server' not in self.headers:
            self.headers['Server'] = \
                'LevIoT Snek v' + VERSION + \
                ' {}/v{}'.format(sys.implementation.name,
                                 '.'.join((str(i) for i in tuple(sys.implementation.version)[:3])))
        if 'Connection' not in self.headers and 'connection' not in self.headers:
            self.headers['Connection'] = "close"
        if 'Content-Type' not in self.headers and 'content-type' not in self.headers:
            self.headers['Content-Type'] = 'text/plain'

    @micropython.native
    def __get_http_head(self):
        return "{} {}{}\r\n".format(
                self.http_version, self.status, (" " + self.status_mesg) if self.status_mesg else '').encode()

    async def write_into(self, writer):
        writer.write(self.__get_http_head())
        await writer.drain()

        for key, val in self.headers.items():
            writer.write("{}: {}\r\n".format(key, val).encode())
            await writer.drain()
        writer.write(b'\r\n')
        await writer.drain()

        if self.body:
            if type(self.body) == str:
                self.body = self.body.encode()
            chunk_size = 256
            for i in range(0, len(self.body), chunk_size):
                writer.write(self.body[i:i + chunk_size])
                await writer.drain()

    @classmethod
    async def not_found(cls, writer):
        await cls(404).write_into(writer)

    @classmethod
    async def bad_request(cls, writer):
        await cls(400).write_into(writer)

    @classmethod
    async def unauthorized(cls, writer, realm="Snek"):
        await cls(401, headers={
            'WWW-Authenticate': 'Basic realm="{}"'.format(realm)
        }).write_into(writer)

    @classmethod
    async def not_acceptable(cls, writer):
        await cls(406).write_into(writer)

    @classmethod
    async def see_other(cls, writer, location: str):
        await cls(303, headers={
            "Location": location
        }).write_into(writer)

    @classmethod
    async def internal_server_error(cls, writer):
        await cls(500).write_into(writer)
