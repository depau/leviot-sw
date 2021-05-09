import micropython
import uasyncio
import utime
from machine import Pin, Signal, PWM

from leviot import constants


@micropython.native
def pulse(pin: Signal):
    pin.on()
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
        self.sr_clock.off()
        self.sr_shift.off()
        self.sr_latch.off()
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
            self.filter_led_cur = self.filter_led_staging

            if self.filter_led_staging == "blink":
                loop = uasyncio.get_event_loop()
                loop.create_task(self.blink_loop())
            else:
                self.s_filter_led.value(self.filter_led_staging)

        if self.sr_cur == self.sr_staging:
            return

        self.sr_latch.off()
        for bit in range(16):
            self.sr_shift.value((self.sr_staging >> bit) & 1 == 1)
            pulse(self.sr_clock)
        pulse(self.sr_latch)
        self.sr_cur = self.sr_staging

    def value(self, bit: int, value):
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

    async def blink_loop(self):
        pwm = PWM(self.s_filter_led)
        while self.filter_led_cur == "blink":
            increment = 1
            duty = 0
            while self.filter_led_cur == "blink" and 0 <= duty <= 1023:
                pwm.duty(duty)
                duty += increment
                await uasyncio.sleep_ms(3)
            increment *= -1
            duty += increment

        pwm.deinit()
        self.s_filter_led.value(self.filter_led_cur)

gpio = GPIOManager()
