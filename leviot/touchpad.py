import micropython
from machine import Pin, TouchPad

from leviot import constants, conf, ulog

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


touchpads = TouchPads()
