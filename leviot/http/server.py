import uasyncio as asyncio

from leviot import conf, ulog
from leviot.constants import FAN_SPEED_MAP
from leviot.http import uhttp, html, ufirewall
from leviot.state import StateTracker

log = ulog.Logger("http_server")


async def close_streams(*streams):
    for stream in streams:
        stream.close()
    for stream in streams:
        await stream.wait_closed()


class HttpServer:
    def __init__(self, leviot):
        # type: ("leviot.main.LevIoT") -> None
        self.leviot = leviot

    async def serve(self):
        await asyncio.start_server(self.on_http_connection, conf.http_listen, conf.http_port)
        log.i("HTTP server up at {}:{}".format(conf.http_listen, conf.http_port))

    async def on_http_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ip, port = reader.get_extra_info('peername')
        log.d("New connection from {}:{}".format(ip, port))

        if not ufirewall.is_allowed(ip):
            log.w("IP not allowed: {}".format(ip))
            await close_streams(writer)
            return

        req = await uhttp.HTTPRequest.parse(reader)

        log.d("{} {}".format(req.method, req.path))

        if getattr(conf, 'http_basic_auth'):
            if not req.check_basic_auth(conf.http_basic_auth):
                log.w("Request has invalid auth")
                await uhttp.HTTPResponse.unauthorized(writer, realm="LevIoT")
                await close_streams(writer)
                return

        if req.method == "GET":
            if req.path == "/" or req.path == "/index.html":
                await self.handle_http_index(req, writer)
            elif req.path == "/priv-api/fan":
                await self.handle_priv_set_fan(req, writer)
            elif req.path == "/priv-api/on":
                await self.handle_priv_set_power(writer, True)
            elif req.path == "/priv-api/off":
                await self.handle_priv_set_power(writer, False)
            else:
                await uhttp.HTTPResponse.not_found(writer)

        else:
            await uhttp.HTTPResponse.not_found(writer)

        await close_streams(writer)

    @staticmethod
    async def handle_http_index(req: uhttp.HTTPRequest, writer: asyncio.StreamWriter):

        await uhttp.HTTPResponse(
            200,
            body=html.index.format(
                power='ON' if StateTracker.power else "OFF",
                speed=FAN_SPEED_MAP[StateTracker.speed]
            ),
            headers={'Content-Type': 'text/html;charset=utf-8'}
        ).write_into(writer)

    async def handle_priv_set_fan(self, req: uhttp.HTTPRequest, writer: asyncio.StreamWriter):
        speed_str = req.query.get("speed", None)
        if not speed_str:
            return await uhttp.HTTPResponse.bad_request(writer)
        try:
            speed = int(speed_str)
            await self.leviot.set_fan_speed(speed)
        except Exception as e:
            print(e)
            return await uhttp.HTTPResponse.bad_request(writer)

        await uhttp.HTTPResponse.see_other(writer, "/")

    async def handle_priv_set_power(self, writer: asyncio.StreamWriter, power: bool):
        try:
            await self.leviot.set_power(power)
        except Exception as e:
            log.e(e)
            return await uhttp.HTTPResponse.internal_server_error(writer)

        await uhttp.HTTPResponse.see_other(writer, "/")
