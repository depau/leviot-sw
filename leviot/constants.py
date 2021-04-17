import network
from micropython import const

# Touch pads
TOUCHPADS = {
    "FAN": const(14),
    "FILTER": const(33),
    "NIGHT": const(13),
    "LIGHT": const(32),
    "LOCK": const(27),
    "POWER": const(4),
    "TIMER": const(15),
}

TOUCHPADS_POLL_INTERVAL_MS = 50
TOUCHPAD_HOLD_TIMEOUT_MS = 3000

# Shift registers
PIN_SR_DS = const(18)
PIN_SR_CLK = const(19)
PIN_SR_LATCH = const(21)
PIN_SR_OUTEN = const(17)

# Directly connected LED
PIN_LED_FILTER = const(26)

# This has been removed since I calculated Pin.value() takes ~200 us anyway (ew slow)
# # Shift register propagation
# # The maximum delay according to the datasheet should be 63 NANOseconds so 1 us is more than enough
# SR_PROP_DELAY_US = 1

# Wireless auth modes
WIFI_AUTHMODES = {
    "open": network.AUTH_OPEN,
    "wep": network.AUTH_WEP,
    "wpa_psk": network.AUTH_WPA_PSK,
    "wpa2_psk": network.AUTH_WPA2_PSK,
    "wpa_wpa2_psk": network.AUTH_WPA_WPA2_PSK
}

FAN_SPEED_MAP = ('Night', 'I', 'II', 'III')

# Shift register pin bits
LED_FILTER = const(-42)  # Not on the shift register but still handled by GPIOManager
LED_V1 = const(15)
LED_V2 = const(14)
LED_V3 = const(13)
LED_2H = const(12)
LED_4H = const(11)
LED_6H = const(10)
LED_8H = const(9)
LED_FAN = const(8)
LED_POWER = const(7)
LED_NIGHT = const(6)
LED_LOCK = const(5)
LED_TIMER = const(4)
FAN_CTL0 = const(3)
FAN_CTL1 = const(2)
FAN_CTL2 = const(1)
FAN_CTL3 = const(0)

ALL_SR_LEDS = const(
    1 << LED_V1 | 1 << LED_V2 | 1 << LED_V3 | 1 << LED_2H | 1 << LED_4H | 1 << LED_6H | 1 << LED_8H
    | 1 << LED_FAN | 1 << LED_POWER | 1 << LED_NIGHT | 1 << LED_LOCK | 1 << LED_TIMER
)

