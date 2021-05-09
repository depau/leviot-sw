import uasyncio
import utime

from leviot import constants, conf, ulog
from leviot.extgpio import gpio
from leviot.http.server import HttpServer
from leviot.mqtt.controller import MQTTController
from leviot.persistence import persistence
from leviot.state import StateTracker
from leviot.touchpad import touchpads

log = ulog.Logger("controller")


class LevIoT:
    def __init__(self):
        self.httpd = HttpServer(self)
        if conf.mqtt_enabled:
            self.mqtt = MQTTController(self)
        self.loop = uasyncio.get_event_loop()
        self.should_stop = False

    def stop(self):
        self.should_stop = True

    async def mainloop(self):
        self.loop.create_task(self.touchpad_loop())

        await self.update_leds()

        if StateTracker.power:
            StateTracker.power = False
            await self.set_power(True)
            persistence.notify_poweron()
        else:
            persistence.notify_poweroff()

        await self.httpd.serve()

        if conf.mqtt_enabled:
            await self.mqtt.start()

        while True:
            await uasyncio.sleep(1)
            await persistence.track()

    async def set_timer(self, time: int):
        log.i("Set timer to {} minutes".format(time))
        timer_running = StateTracker.timer_left > 0
        StateTracker.timer_left = time

        if conf.mqtt_enabled:
            await self.mqtt.notify_timer()

        if not timer_running and time > 0:
            self.loop.create_task(self.timer_loop())

    async def timer_loop(self):
        if not StateTracker.power:
            await self.set_power(True)

        t1 = t2 = 0
        while StateTracker.timer_left > 0:
            await uasyncio.sleep_ms(60 * 1000 - (t2 - t1))
            t1 = utime.time_ns() // 1000
            StateTracker.timer_left -= 1
            log.i("Timer {} minutes left".format(StateTracker.timer_left))

            if conf.mqtt_enabled:
                await self.mqtt.notify_timer()
            t2 = utime.time_ns() // 1000

        if StateTracker.power:
            await self.set_power(False)
        log.i("Timer done")

    async def touchpad_loop(self):
        lock_hold_t = 0
        filter_hold_t = 0

        while not self.should_stop:
            pressed = touchpads.poll()

            if "LOCK" not in pressed:
                lock_hold_t = 0
            else:
                lock_hold_t += constants.TOUCHPADS_POLL_INTERVAL_MS
                if lock_hold_t >= constants.TOUCHPAD_HOLD_TIMEOUT_MS:
                    lock_hold_t = 0

                    await self.set_lock(not StateTracker.lock)

            if "FILTER" not in pressed:
                filter_hold_t = 0
            elif not StateTracker.lock:
                filter_hold_t += constants.TOUCHPADS_POLL_INTERVAL_MS
                if filter_hold_t >= constants.TOUCHPAD_HOLD_TIMEOUT_MS:
                    filter_hold_t = 0

                    if persistence.replacement_due or persistence.dusting_due or StateTracker.user_maint:
                        persistence.notify_maintenance()
                    else:
                        StateTracker.user_maint = not StateTracker.user_maint
                    with gpio:
                        await self.update_leds()

            if not StateTracker.lock:
                for pad in pressed:
                    if pad == "POWER":
                        await self.set_power(not StateTracker.power)

                    elif pad == "FAN":
                        if StateTracker.speed == 0:
                            await self.set_fan_speed(StateTracker.prev_speed or 1)
                        else:
                            await self.set_fan_speed(1 + (StateTracker.speed % 3))

                    elif pad == "NIGHT":
                        if StateTracker.speed == 0:
                            await self.set_fan_speed(StateTracker.prev_speed)
                        else:
                            await self.set_fan_speed(0)

                    elif pad == "LIGHT":
                        await self.set_lights(not StateTracker.lights)

                    elif pad == "TIMER":
                        newtime = StateTracker.timer_left + 2 * 60
                        if newtime > 9 * 60:
                            newtime = 0
                        await self.set_timer(newtime)

            await uasyncio.sleep_ms(constants.TOUCHPADS_POLL_INTERVAL_MS)

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

            gpio.value(constants.LED_TIMER, StateTracker.timer_left > 0)
            gpio.value(constants.LED_2H, 0 < StateTracker.timer_left <= 2 * 60)
            gpio.value(constants.LED_4H, 2 * 60 < StateTracker.timer_left <= 4 * 60)
            gpio.value(constants.LED_6H, 4 * 60 < StateTracker.timer_left <= 6 * 60)
            gpio.value(constants.LED_8H, 6 * 60 < StateTracker.timer_left)

            if persistence.replacement_due or StateTracker.user_maint:
                gpio.value(constants.LED_FILTER, "blink")
            else:
                gpio.value(constants.LED_FILTER, persistence.dusting_due)

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
            persistence.notify_poweron()

        else:
            StateTracker.timer_left = 0
            with gpio:
                gpio.value(constants.FAN_CTL0, False)
                gpio.value(constants.FAN_CTL1, False)
                gpio.value(constants.FAN_CTL2, False)
                gpio.value(constants.FAN_CTL3, False)
                await self.update_leds()

            persistence.notify_poweron()

    async def set_fan_speed(self, speed: int):
        if not 0 <= speed <= 3:
            raise ValueError("Fan speed must be within 0 and 3")

        StateTracker.prev_speed = StateTracker.speed
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

    async def set_lights(self, lights: bool):
        StateTracker.lights = lights
        with gpio:
            await self.update_leds()

        log.i("Set lights to {}".format(lights))

    async def set_lock(self, lock: bool):
        StateTracker.lock = lock
        with gpio:
            await self.update_leds()

        log.i("Set lock to {}".format(lock))
