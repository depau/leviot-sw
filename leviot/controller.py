import uasyncio

from leviot import constants
from leviot.extgpio import gpio
from leviot.http.server import HttpServer
from leviot.state import StateTracker
from leviot.usage_timer import usage


class LevIoT:
    def __init__(self):
        self.httpd = HttpServer(self)

    async def mainloop(self):
        await self.update_leds()
        await self.httpd.serve()
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
        if on == StateTracker.power:
            return
        StateTracker.power = on

        if on:
            # Kickstart fan asynchronously
            async def kickstart_fan():
                speed = StateTracker.speed
                await self.set_fan_speed(3)
                await uasyncio.sleep(1)
                await self.set_fan_speed(speed)

            uasyncio.get_event_loop().create_task(kickstart_fan())

        else:
            with gpio:
                gpio.value(constants.FAN_CTL0, False)
                gpio.value(constants.FAN_CTL1, False)
                gpio.value(constants.FAN_CTL2, False)
                gpio.value(constants.FAN_CTL3, False)
                await self.update_leds()

    async def set_fan_speed(self, speed: int):
        if not 0 <= speed <= 3:
            raise ValueError("Fan speed must be within 0 and 3")

        StateTracker.speed = speed

        if not StateTracker.power:
            return

        with gpio:
            gpio.value(constants.FAN_CTL0, StateTracker.speed == 0 and StateTracker.power)
            gpio.value(constants.FAN_CTL1, StateTracker.speed == 1 and StateTracker.power)
            gpio.value(constants.FAN_CTL2, StateTracker.speed == 2 and StateTracker.power)
            gpio.value(constants.FAN_CTL3, StateTracker.speed == 3 and StateTracker.power)
            await self.update_leds()
