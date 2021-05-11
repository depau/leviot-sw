import math

import micropython
import utime
from machine import Pin, TouchPad

from leviot import constants, conf, ulog
from leviot.extgpio import gpio

log = ulog.Logger("touchpad")


class TouchPads:
    def __init__(self):
        self.tp = {}
        self.debounce_off = set()
        self.debounce_on = {}

        for name, pin in constants.TOUCHPADS.items():
            self.tp[name] = TouchPad(Pin(pin))
            self.debounce_on[name] = 0

        log.i("Touchpad values:")
        accum = 0
        for name, value in self.read_all():
            accum += value
            log.i(" - {}: {}".format(name, value))

    def read_all(self):
        for name, tp in self.tp.items():
            yield name, tp.read()

    @micropython.native
    def poll(self) -> list:
        for name, value in self.read_all():
            if value < conf.touchpad_calibration_val[name] and name not in self.debounce_off:
                self.debounce_on[name] += 1
            elif value >= conf.touchpad_calibration_val[name] and name in self.debounce_off:
                self.debounce_on[name] = 0
                self.debounce_off.remove(name)

        pressed = []

        for name, occurrences in self.debounce_on.items():
            if occurrences > 4 or (name in ("FILTER", "LOCK") and occurrences > 0):
                pressed.append(name)
                self.debounce_on[name] = 0

                if name not in ("FILTER", "LOCK"):
                    self.debounce_off.add(name)

        return pressed

    def calibrate(self):
        gpio.init()
        with gpio:
            gpio.leds(False)

        print()
        print("Touchpad calibration")
        result = {}

        print("Tap the pad that blinks (or the closest one) multiple times as you normally would during normal "
              "operation")

        for tp, led in constants.TOUCHPAD_LED_MAPPING.items():
            readings = []

            print("{} \t".format(tp), end="")

            interval = 5
            for i in range(0, 5000, interval):  # 5s
                led_on = False
                if i % (500/interval):
                    led_on = not led_on
                    with gpio:
                        gpio.value(led, led_on)
                readings.append(self.tp[tp].read())
                utime.sleep_ms(interval)

            with gpio:
                gpio.off(led)

            pin_min = min(readings)
            pin_max = max(readings)
            pin_mid = (pin_min + pin_max) // 2
            pin_qmid = int(math.sqrt((pin_min ** 2 + pin_max ** 2) / 2))
            pin_25p = int((pin_max - pin_min) * 0.25 + pin_min)

            print("{:>5} min  {:>5} max  {:>5} mid  {:>5} qmid  {:>5} 25%".format(
                pin_min, pin_max, pin_mid, pin_qmid, pin_25p))

            result[tp] = pin_25p

        print("Calibration result: (replace in config to save it)\n")
        print("touchpad_calibration_val = {")
        for name, value in result.items():
            print('    "{}": const({}),'.format(name, value))
        print("}\n")

        conf.touchpad_calibration_val = result
        print("Calibration data applied, run with 'run' to test")


touchpads = TouchPads()
