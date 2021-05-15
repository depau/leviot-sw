import esp32
import micropython
from machine import Pin, TouchPad

from leviot import constants, ulog

log = ulog.Logger("touchpad")

esp32.touch_set_cycles(500, 500)


# Port of https://github.com/valerionew/colors-of-italy/blob/2dd357fbdd820e67e3c0b994458b36cffec10506/firmware/src/main.cpp#L29-L165
class LowPassFilter:
    def __init__(self, alpha: float = 0., value: float = 0.):
        self.alpha = alpha
        self.value = value

    def update(self, sample: float) -> float:
        self.value += (sample - self.value) * self.alpha
        return self.value


class CircularAdder:
    def __init__(self, size: int):
        self.size = size
        self.buf = [0] * size
        self.pos = 0

    def update(self, value: float) -> float:
        # noinspection PyTypeChecker
        self.buf[self.pos] = value
        self.pos += 1
        self.pos %= self.size
        return sum(self.buf)


class MovingAverage(CircularAdder):
    def update(self, value: float):
        return super(MovingAverage, self).update(value) / self.size


class FilteredTouchpad(TouchPad):
    def __init__(self, pin: Pin, threshold: int = 3.5, outlier_threshold: int = 100,
                 steady_alpha=0.0005, recover_alpha=0.1):
        super(FilteredTouchpad, self).__init__(pin)
        self.threshold = threshold
        self.outlier_threshold = outlier_threshold
        self.steady_alpha = steady_alpha
        self.recover_alpha = recover_alpha

        self.old_reading = self.read()
        self._init = True
        self._pressed = False

        self.lpf = LowPassFilter(0.001, self.old_reading)
        self.adder = CircularAdder(5)
        self.avg = MovingAverage(5)

    @property
    def pressed(self) -> bool:
        old_reading = self.old_reading
        reading = self.old_reading = self.avg.update(self.read())

        if abs(reading - old_reading) < self.outlier_threshold:
            lp_filtered = self.lpf.update(reading)
            box_filtered = self.adder.update(lp_filtered - reading)
            # print(box_filtered, box_filtered > self.threshold and 5 or 0)
            self._pressed = box_filtered > self.threshold

            self.lpf.alpha = self.steady_alpha if box_filtered > 0 else self.recover_alpha

        # Discard initial "pressed" readings until we get a "not pressed"
        if self._pressed and self._init:
            return False
        elif self._init:
            self._init = False

        return self._pressed


class TouchPads:
    def __init__(self):
        self.tp = {}
        self.debounce_off = set()
        self.debounce_on = {}

        for name, pin in constants.TOUCHPADS.items():
            self.tp[name] = FilteredTouchpad(Pin(pin))
            self.debounce_on[name] = 0

    def read_all(self):
        for name, tp in self.tp.items():
            yield name, tp.pressed

    @micropython.native
    def poll(self) -> list:
        for name, pressed in self.read_all():
            if pressed and name not in self.debounce_off:
                self.debounce_on[name] += 1
            elif pressed and name in self.debounce_off:
                self.debounce_on[name] = 0
                self.debounce_off.remove(name)

        touchpads_pressed = []

        for name, occurrences in self.debounce_on.items():
            if occurrences > 4 or (name in ("FILTER", "LOCK") and occurrences > 0):
                touchpads_pressed.append(name)
                self.debounce_on[name] = 0

                if name not in ("FILTER", "LOCK"):
                    self.debounce_off.add(name)

        return touchpads_pressed


touchpads = TouchPads()
