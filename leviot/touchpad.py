from machine import Pin, TouchPad

from leviot import constants, conf


class TouchPads:
    def __init__(self):
        self.tp = {}
        self.debounce = set()

        for name, pin in constants.TOUCHPADS.items():
            self.tp[name] = TouchPad(Pin(pin))

    def poll(self) -> list:
        new = []
        for name, tp in self.tp.items():
            if tp.read() < conf.tp_threshold:
                if name in self.debounce:
                    continue
                new.append(name)
                # Do not debounce pads that are supposed to be held down
                if name not in ("FILTER", "LOCK"):
                    self.debounce.add(name)
            else:
                if name in self.debounce:
                    self.debounce.remove(name)
        return new


touchpads = TouchPads()
