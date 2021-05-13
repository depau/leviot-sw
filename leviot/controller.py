import uasyncio
import utime

from leviot import constants, conf, ulog
from leviot.extgpio import gpio
from leviot.http.server import HttpServer
from leviot.mqtt.controller import MQTTController
from leviot.persistence import persistence
from leviot.state import state_tracker
from leviot.touchpad import touchpads

log = ulog.Logger("controller")


class LevIoT:
    def __init__(self):
        self.httpd = HttpServer(self)
        if conf.mqtt_enabled:
            self.mqtt = MQTTController(self)
        self.loop = uasyncio.get_event_loop()
        self.should_stop = False
        self.is_kickstarting = False

    def stop(self):
        self.should_stop = True

    async def mainloop(self):
        self.loop.create_task(self.touchpad_loop())

        await self.update_leds()

        if state_tracker.power:
            state_tracker.power = False
            await self.set_power(True, cause="persistence")
            persistence.notify_poweron()
        else:
            persistence.notify_poweroff()

        await self.httpd.serve()

        if conf.mqtt_enabled:
            self.loop.create_task(self.start_mqtt())

        while True:
            await uasyncio.sleep(1)
            await persistence.track()

    async def start_mqtt(self):
        await self.mqtt.start()
        ulog.set_mqtt(self.mqtt)

    async def set_timer(self, time: int, cause="unknown"):
        log.i("Set timer to {} minutes (cause: {})".format(time, cause))
        timer_running = state_tracker.timer_left > 0
        state_tracker.timer_left = time

        with gpio:
            await self.update_leds()

        if conf.mqtt_enabled:
            await self.mqtt.notify_timer()

        if not timer_running and time > 0:
            self.loop.create_task(self.timer_loop())

    async def timer_loop(self):
        if not state_tracker.power:
            await self.set_power(True, cause="timer")

        t1 = t2 = 0
        while state_tracker.timer_left > 0:
            await uasyncio.sleep_ms(60 * 1000 - (t2 - t1))
            t1 = utime.time_ns() // 1000
            state_tracker.timer_left -= 1
            log.i("Timer {} minutes left".format(state_tracker.timer_left))

            if conf.mqtt_enabled:
                await self.mqtt.notify_timer()
            t2 = utime.time_ns() // 1000

        if state_tracker.power:
            await self.set_power(False, cause="timer")
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

                    await self.set_lock(not state_tracker.lock, cause="touchpad")

            if "FILTER" not in pressed:
                filter_hold_t = 0
            elif not state_tracker.lock:
                filter_hold_t += constants.TOUCHPADS_POLL_INTERVAL_MS
                if filter_hold_t >= constants.TOUCHPAD_HOLD_TIMEOUT_MS:
                    filter_hold_t = 0

                    if persistence.replacement_due or persistence.dusting_due or state_tracker.user_maint:
                        persistence.notify_maintenance()
                    else:
                        state_tracker.user_maint = not state_tracker.user_maint
                    with gpio:
                        await self.update_leds()

            if not state_tracker.lock:
                for pad in pressed:
                    if pad == "POWER":
                        await self.set_power(not state_tracker.power, cause="touchpad")

                    elif pad == "FAN":
                        if state_tracker.speed == 0:
                            await self.set_fan_speed(state_tracker.prev_speed or 1, cause="touchpad")
                        else:
                            await self.set_fan_speed(1 + (state_tracker.speed % 3), cause="touchpad")

                    elif pad == "NIGHT":
                        if state_tracker.speed == 0:
                            await self.set_fan_speed(state_tracker.prev_speed, cause="touchpad")
                        else:
                            await self.set_fan_speed(0, cause="touchpad")

                    elif pad == "LIGHT":
                        await self.set_lights(not state_tracker.lights, cause="touchpad")

                    elif pad == "TIMER":
                        newtime = state_tracker.timer_left + 2 * 60
                        if newtime > 9 * 60:
                            newtime = 0
                        await self.set_timer(newtime, cause="touchpad")

            await uasyncio.sleep_ms(constants.TOUCHPADS_POLL_INTERVAL_MS)

    async def update_leds(self):
        if not state_tracker.lights:
            gpio.leds(False)
        else:
            gpio.value(constants.LED_POWER, state_tracker.power)
            gpio.value(constants.LED_LOCK, state_tracker.lock and state_tracker.power)
            gpio.value(constants.LED_FAN, state_tracker.speed > 0 and state_tracker.power)

            gpio.value(constants.LED_NIGHT, state_tracker.speed == 0 and state_tracker.power)
            gpio.value(constants.LED_V1, state_tracker.speed == 1 and state_tracker.power)
            gpio.value(constants.LED_V2, state_tracker.speed == 2 and state_tracker.power)
            gpio.value(constants.LED_V3, state_tracker.speed == 3 and state_tracker.power)

            gpio.value(constants.LED_TIMER, state_tracker.timer_left > 0)
            gpio.value(constants.LED_2H, 0 < state_tracker.timer_left <= 2 * 60)
            gpio.value(constants.LED_4H, 2 * 60 < state_tracker.timer_left <= 4 * 60)
            gpio.value(constants.LED_6H, 4 * 60 < state_tracker.timer_left <= 6 * 60)
            gpio.value(constants.LED_8H, 6 * 60 < state_tracker.timer_left)

            if persistence.replacement_due or state_tracker.user_maint:
                gpio.value(constants.LED_FILTER, "blink")
            else:
                gpio.value(constants.LED_FILTER, persistence.dusting_due)

    async def set_power(self, on: bool, cause="unknown"):
        state_tracker.power = on

        if conf.mqtt_enabled:
            self.loop.create_task(self.mqtt.notify_power())

        log.i("Set power to {} (cause: {})".format(on, cause))

        if on:
            # Kickstart fan asynchronously
            async def kickstart_fan():
                speed = state_tracker.speed
                await self.set_fan_speed(3, cause="kickstart")
                await uasyncio.sleep(1)
                await self.set_fan_speed(speed, cause="kickstart")

            uasyncio.get_event_loop().create_task(kickstart_fan())
            persistence.notify_poweron()

        else:
            state_tracker.timer_left = 0
            with gpio:
                gpio.value(constants.FAN_CTL0, False)
                gpio.value(constants.FAN_CTL1, False)
                gpio.value(constants.FAN_CTL2, False)
                gpio.value(constants.FAN_CTL3, False)
                await self.update_leds()

            persistence.notify_poweron()

    async def set_fan_speed(self, speed: int, cause="unknown"):
        if not 0 <= speed <= 3:
            raise ValueError("Fan speed must be within 0 and 3")

        if cause == "kickstart":
            self.is_kickstarting = True
        else:
            while self.is_kickstarting:
                log.d("Set speed delayed due to kickstart")
                await uasyncio.sleep(1)

        try:
            state_tracker.prev_speed = state_tracker.speed
            state_tracker.speed = speed

            log.i("Set speed to {} (cause: {})".format(speed, cause))

            if conf.mqtt_enabled:
                self.loop.create_task(self.mqtt.notify_speed())

            if not state_tracker.power:
                return

            with gpio:
                gpio.value(constants.FAN_CTL0, state_tracker.speed == 0 and state_tracker.power)
                gpio.value(constants.FAN_CTL1, state_tracker.speed == 1 and state_tracker.power)
                gpio.value(constants.FAN_CTL2, state_tracker.speed == 2 and state_tracker.power)
                gpio.value(constants.FAN_CTL3, state_tracker.speed == 3 and state_tracker.power)
                await self.update_leds()
        finally:
            if cause == "kickstart":
                self.is_kickstarting = False

    async def set_lights(self, lights: bool, cause="unknown"):
        state_tracker.lights = lights
        with gpio:
            await self.update_leds()

        log.i("Set lights to {} (cause: {})".format(lights, cause))

    async def set_lock(self, lock: bool, cause="unknown"):
        state_tracker.lock = lock
        with gpio:
            await self.update_leds()

        log.i("Set lock to {} (cause: {})".format(lock, cause))
