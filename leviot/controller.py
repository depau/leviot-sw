import uasyncio

from leviot import constants, conf, ulog
from leviot.extgpio import gpio
from leviot.http.server import HttpServer
from leviot.mqtt.controller import MQTTController
from leviot.state import StateTracker
from leviot.usage_timer import usage

log = ulog.Logger("controller")

class LevIoT:
    def __init__(self):
        self.httpd = HttpServer(self)
        if conf.mqtt_enabled:
            self.mqtt = MQTTController(self)
        self.loop = uasyncio.get_event_loop()

    async def mainloop(self):
        await self.update_leds()
        await self.httpd.serve()
        if conf.mqtt_enabled:
            await self.mqtt.start()

        usage.notify_poweroff()

        while True:
            await uasyncio.sleep(60)
            await usage.track()

    async def update_leds(self):
        if not StateTracker.lights:
            gpio.leds(False)
        else:
            gpio.value(constants.LED_POWER, StateTracker.power)
            gpio.value(constants.LED_LOCK, StateTracker.lock and StateTracker.power)
            gpio.value(constants.LED_FAN, StateTracker.speed > 0 and StateTracker.power)

            gpio.value(constants.LED_NIGHT, StateTracker.speed == 0 and StateTracker.power)
            gpio.value(constants.LED_V1, StateTracker.speed == 1 and StateTracker.power)
            gpio.value(constants.LED_V2, StateTracker.speed == 2 and StateTracker.power)
            gpio.value(constants.LED_V3, StateTracker.speed == 3 and StateTracker.power)
            # TODO: timer
        gpio.value(constants.LED_FILTER, StateTracker.filter_out)

    async def set_power(self, on: bool):
        StateTracker.power = on

        if conf.mqtt_enabled:
            self.loop.create_task(self.mqtt.notify_power())

        log.i("Set power to {}".format(on))

        if on:
            # Kickstart fan asynchronously
            async def kickstart_fan():
                speed = StateTracker.speed
                await self.set_fan_speed(3)
                await uasyncio.sleep(1)
                await self.set_fan_speed(speed)

            uasyncio.get_event_loop().create_task(kickstart_fan())
            usage.notify_poweron()

        else:
            with gpio:
                gpio.value(constants.FAN_CTL0, False)
                gpio.value(constants.FAN_CTL1, False)
                gpio.value(constants.FAN_CTL2, False)
                gpio.value(constants.FAN_CTL3, False)
                await self.update_leds()

            usage.notify_poweron()

    async def set_fan_speed(self, speed: int):
        if not 0 <= speed <= 3:
            raise ValueError("Fan speed must be within 0 and 3")

        StateTracker.speed = speed

        log.i("Set speed to {}".format(speed))

        if conf.mqtt_enabled:
            self.loop.create_task(self.mqtt.notify_speed())

        if not StateTracker.power:
            return

        with gpio:
            gpio.value(constants.FAN_CTL0, StateTracker.speed == 0 and StateTracker.power)
            gpio.value(constants.FAN_CTL1, StateTracker.speed == 1 and StateTracker.power)
            gpio.value(constants.FAN_CTL2, StateTracker.speed == 2 and StateTracker.power)
            gpio.value(constants.FAN_CTL3, StateTracker.speed == 3 and StateTracker.power)
            await self.update_leds()
