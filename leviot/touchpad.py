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
        self.debounce = set()

        for name, pin in constants.TOUCHPADS.items():
            self.tp[name] = TouchPad(Pin(pin))

        log.i("Touchpad values:")
        accum = 0
        for name, value in self.read_all():
            accum += value
            log.i(" - {}: {}".format(name, value))

        if conf.tp_threshold <= 0:
            avg = accum / len(constants.TOUCHPADS)
            conf.tp_threshold = avg - 20
            log.i("Average: {}, threshold set to {}".format(avg, conf.tp_threshold))

    def read_all(self):
        for name, tp in self.tp.items():
            yield name, tp.read()

    @micropython.native
    def poll(self) -> list:
        new = []
        for name, value in self.read_all():
            if value < conf.tp_threshold and name not in self.debounce:
                new.append(name)
                # Do not debounce pads that are supposed to be held down
                if name not in ("FILTER", "LOCK"):
                    self.debounce.add(name)
            elif value >= conf.tp_threshold and name in self.debounce:
                self.debounce.remove(name)
        return new

    def calibrate(self):
        gpio.init()
        print()
        print("Touchpad calibration")
        all_min = 0xFFFFFFFF
        all_max = 0
        all_mid = []
        all_qmid = []

        print("Tap the pad that blinks (or the closest one) multiple times as you normally would during normal "
              "operation")

        for tp, led in constants.TOUCHPAD_LED_MAPPING.items():
            readings = []

            print("{} \t".format(tp), end="")

            for i in range(0, 100 * 10 * 5, 100):  # 5s
                led_on = False
                if i % 500:
                    led_on = not led_on
                    with gpio:
                        gpio.value(led, led_on)
                readings.append(self.tp[tp].read())
                utime.sleep_ms(100)

            with gpio:
                gpio.off(led)

            pin_min = min(readings)
            pin_max = max(readings)
            pin_mid = (pin_min + pin_max) // 2
            pin_qmid = int(math.sqrt((pin_min ** 2 + pin_max ** 2) / 2))
            all_mid.append(pin_mid)
            all_qmid.append(pin_qmid)
            if pin_min < all_min:
                all_min = pin_min
            if pin_max > all_max:
                all_max = pin_max

            print("{:>5} min  {:>5} max  {:>5} mid  {:>5} qmid".format(pin_min, pin_max, pin_mid, pin_qmid))

        print()
        print("All {:>5} min  {:>5} max".format(all_min, all_max))
        print("All mid values:", all_mid)
        print("All quadratic mid values:", all_qmid)


touchpads = TouchPads()
