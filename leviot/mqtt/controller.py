import uasyncio

from leviot import conf, ulog
from leviot.state import StateTracker
from mqtt_as.timeout import MQTTClient

log = ulog.Logger("mqtt")


class MQTTController:
    def __init__(self, leviot):
        # type: ("leviot.main.LevIoT") -> None

        self.leviot = leviot

        if not conf.mqtt_prefix:
            raise ValueError("Invalid mqtt_prefix in config")
        if not conf.mqtt_identifier:
            raise ValueError("Invalid mqtt_identifier in config")

        self.base_topic = conf.mqtt_prefix + "/" + conf.mqtt_identifier
        self.state_topic = self.base_topic + "/$state"
        self.loop = uasyncio.get_event_loop()

        conf.mqtt_config.update({
            "will": (self.state_topic, "lost", True, 1),
            "connect_coro": self._on_connect,
            "wifi_coro": self._on_wlan_change,
            "subs_cb": self._on_message_sync,
        })

        self.client = MQTTClient(conf.mqtt_config)

    async def start(self):
        await self.client.connect()
        log.i("MQTT started")

    async def _on_connect(self, _):
        log.i("MQTT connected")
        await self.client.subscribe(self.base_topic + "/fan/speed/set")
        await self.client.subscribe(self.base_topic + "/fan/power/set")

        await self.client.publish(self.state_topic, "init", retain=True, timeout=60)

        if conf.homie_autodiscovery:
            # Device attributes
            await self.client.publish(self.base_topic + "/$homie", "4.0.0", retain=True, timeout=60)
            await self.client.publish(self.base_topic + "/$name", conf.homie_friendly_name, retain=True, timeout=60)
            await self.client.publish(self.base_topic + "/$nodes", "fan", retain=True, timeout=60)
            await self.client.publish(self.base_topic + "/$implementation", "LevIoT Snek", retain=True, timeout=60)

            # Fan speed node attributes
            node = self.base_topic + "/fan"
            await self.client.publish(node + "/$name", "Fan", retain=True, timeout=60)
            await self.client.publish(node + "/$type", "Air purifier", retain=True, timeout=60)
            await self.client.publish(node + "/$properties", "speed,power", retain=True, timeout=60)

            # Power property attributes
            prop = node + "/power"
            await self.client.publish(prop + "/$name", "Power", retain=True, timeout=60)
            await self.client.publish(prop + "/$datatype", "boolean", retain=True, timeout=60)
            await self.client.publish(prop + "/$settable", "true", retain=True, timeout=60)

            # Fan speed property attributes
            prop = node + "/speed"
            await self.client.publish(prop + "/$name", "Fan speed", retain=True, timeout=60)
            await self.client.publish(prop + "/$datatype", "integer", retain=True, timeout=60)
            await self.client.publish(prop + "/$settable", "true", retain=True, timeout=60)
            await self.client.publish(prop + "/$format", "0:3", retain=True, timeout=60)

        await self.notify_power()
        await self.notify_speed()
        await self.client.publish(self.state_topic, "ready", retain=True, timeout=60)
        log.i("MQTT ready")

    async def _on_wlan_change(self, connected: bool):
        if connected and self.client.isconnected():
            await self.client.publish(self.state_topic, "ready", retain=True, timeout=60)

    def _on_message_sync(self, topic: bytes, payload: bytes, retained: bool):
        self.loop.create_task(self._on_message(topic, payload, retained))

    async def _on_message(self, topic: bytes, payload: bytes, retained: bool):
        topic = topic.decode()
        if topic.endswith("/fan/power/set"):
            if payload not in (b"true", b"false"):
                raise ValueError("Invalid MQTT payload for Homie bool: {}".format(payload))
            await self.leviot.set_power(payload == b"true")

        elif topic.endswith("/fan/speed/set"):
            speed = int(payload)
            if not 0 <= speed <= 3:
                raise ValueError("Invalid MQTT fan speed: {}".format(speed))
            await self.leviot.set_fan_speed(speed)

    async def notify_power(self):
        await self.client.publish(self.base_topic + "/fan/power", str(StateTracker.power).lower(), retain=True,
                                  timeout=60)

    async def notify_speed(self):
        await self.client.publish(self.base_topic + "/fan/speed", str(StateTracker.speed), retain=True, timeout=60)
