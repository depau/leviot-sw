class Pin:
    OUT = "OUT"
    IN = "IN"

    PULL_UP = "PULL_UP"
    PULL_DOWN = "PULL_DOWN"

    def __init__(self, *args, invert=False, **kwargs):
        self.args = args
        if isinstance(args[0], Pin):
            self.args = args[0].args
        self.invert = invert

    def on(self):
        print(f"STUB: machine.Pin{self.args}.on() invert {self.invert}")

    def off(self):
        print(f"STUB: machine.Pin{self.args}.off() invert {self.invert}")

    def value(self, *a):
        print(f"STUB: machine.Pin{self.args}.value{a} invert {self.invert}")
        if self.args[0] == 0:
            return 1
        return 0


class Signal(Pin):
    pass


class PWM:
    def __init__(self, *a):
        self.args = a

    def freq(self, *a):
        print(f"STUB: machine.PWM{self.args},freq({a})")

    def deinit(self):
        print(f"STUB: machine.PWM{self.args},deinit()")


class UART:
    def __init__(self, *a):
        pass

    def init(self, **kwargs):
        print(f"STUB: machine.UART,init({kwargs})")

    def deinit(self):
        print(f"STUB: machine.UART,deinit()")


class TouchPad:
    def __init__(self, pin: Pin):
        print(f"STUB: machine.TouchPad({pin})")

    def read(self):
        return 100


def freq(new_clock, **kw):
    print("OVERCLOCCCKKKK OMH SUCH SPEED VERY FAST {}".format(new_clock))


def unique_id():
    return b"yolo"


def reset():
    raise KeyboardInterrupt
