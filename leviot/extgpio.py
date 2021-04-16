import micropython
from machine import Pin, Signal

from leviot import constants


@micropython.native
def pulse(pin: Signal):
    # utime.sleep_us(constants.SR_PROP_DELAY_US)
    pin.on()
    # utime.sleep_us(constants.SR_PROP_DELAY_US)
    pin.off()


class GPIOManager:
    """
    Helper class to handle the connected shift register + GPIOs transparently.
    """

    def __init__(self):
        self.sr_cur = -1
        self.sr_staging = 0
        self.filter_led_cur = False
        self.filter_led_staging = False

        self.s_filter_led = Signal(Pin(constants.PIN_LED_FILTER, Pin.OUT), invert=False)
        self.s_filter_led.off()

        self.sr_shift = Signal(Pin(constants.PIN_SR_DS, Pin.OUT), invert=False)
        self.sr_latch = Signal(Pin(constants.PIN_SR_LATCH, Pin.OUT), invert=False)
        self.sr_clock = Signal(Pin(constants.PIN_SR_CLK, Pin.OUT), invert=False)
        self.sr_outen = Signal(Pin(constants.PIN_SR_OUTEN, Pin.OUT), invert=True)
        self.sr_outen.off()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()

    def init(self):
        self.sr_cur = -1
        self.sr_staging = 0
        self.commit()
        self.sr_outen.on()

    @micropython.native
    def commit(self) -> None:
        if self.filter_led_cur != self.filter_led_staging:
            self.s_filter_led.value(self.filter_led_staging)
            self.filter_led_cur = self.filter_led_staging

        if self.sr_cur == self.sr_staging:
            return

        for bit in range(16):
            self.sr_shift.value((self.sr_staging >> bit) & 1 == 1)
            pulse(self.sr_clock)
        pulse(self.sr_latch)
        self.sr_cur = self.sr_staging

    def value(self, bit: int, value: bool):
        if bit == constants.LED_FILTER:
            self.filter_led_staging = value
            return

        if value:
            self.sr_staging |= 1 << bit
        else:
            self.sr_staging &= ~(1 << bit)

    def on(self, bit: int):
        self.value(bit, True)

    def off(self, bit: int):
        self.value(bit, False)

    def leds(self, value: bool):
        """
        Helper function to set all LEDs to some value
        """
        self.filter_led_staging = value
        if value:
            self.sr_staging |= constants.ALL_SR_LEDS
        else:
            self.sr_staging &= ~constants.ALL_SR_LEDS

    def all(self, value: bool):
        self.filter_led_staging = value
        if value:
            self.sr_staging = 0xffff
        else:
            self.sr_staging = 0


gpio = GPIOManager()
