VERSION = "0.1"

import esp
import esp32
import uasyncio
import usys
import utime
import machine
from machine import Pin, Signal

from leviot import network, constants, ulog
from leviot.controller import LevIoT
from leviot.extgpio import gpio
from leviot import conf

log = ulog.Logger("init")


def main():
    # Enable Dynamic Frequency Scaling
    machine.freq(conf.cpu_freq_perf, min_freq=conf.cpu_freq_idle)

    io0_pin = Pin(0, Pin.IN, Pin.PULL_UP)
    user_interrupted = False

    loop = uasyncio.get_event_loop()

    log.i("Starting up LevIoT")

    try:
        log.d("Init GPIO")
        gpio.init()

        log.i("Hold the BOOT button now to interrupt boot")
        # LED test
        with gpio:
            gpio.leds(True)

        utime.sleep_ms(1000)

        with gpio:
            gpio.leds(False)

        # Do not run if IO0 is held right after boot
        if not io0_pin.value():
            log.i("Interrupting startup since the BOOT button is pressed")
            user_interrupted = True
            return

        # Power saving
        #esp.sleep_type(esp.SLEEP_LIGHT)
        esp32.wake_on_touch(True)

        log.i("Connecting to Wi-Fi")
        network.up()
        log.i("Wi-Fi connected")

        loop = uasyncio.get_event_loop()
        loop.create_task(network.ensure_up())

        log.d("Starting controller coroutines")
        leviot = LevIoT()

        loop.run_until_complete(leviot.mainloop())
        log.e("Main loop exited!")
    except Exception as e:
        log.e(e)
        usys.print_exception(e)
    finally:
        log.i("Safely shutting down")
        # Turn everything off
        sr_outen = Signal(Pin(constants.PIN_SR_OUTEN, Pin.OUT), invert=True)
        sr_outen.off()

        # Turn on red (filter) LED
        red_led = Pin(constants.PIN_LED_FILTER, Pin.OUT)
        red_led.on()

        if not user_interrupted:
            log.i("Resetting microcontroller")
            # machine.reset()
