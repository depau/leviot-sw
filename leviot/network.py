import network
import uasyncio
import usys
import utime

from leviot import conf as cfg, constants, ulog
from leviot.extgpio import gpio

wlan = None

log = ulog.Logger("network")


def up() -> network.WLAN:
    global wlan

    led_on = True
    with gpio:
        gpio.on(constants.LED_POWER)

    if cfg.wifi_mode == "sta":
        while True:
            try:
                wlan = network.WLAN(network.STA_IF)
                if not wlan.active() or not wlan.isconnected():
                    wlan.active(True)
                    wlan.config(dhcp_hostname=cfg.hostname)
                    wlan.connect(cfg.wifi_ssid, cfg.wifi_key)

                    while not wlan.isconnected():
                        utime.sleep_ms(500)
                        with gpio:
                            led_on = not led_on
                            gpio.value(constants.LED_POWER, led_on)
                log.i("Connected with IP " + wlan.ifconfig()[0])
                break
            except Exception as e:
                log.e("Failed to connect to Wi-Fi, will retry")
                usys.print_exception(e)
                try:
                    wlan.active(False)
                    utime.sleep_ms(500)
                except Exception as e:
                    usys.print_exception(e)
                    pass

    elif cfg.wifi_mode == "ap":
        wlan = network.WLAN(network.AP_IF)
        wlan.config(
            essid=cfg.wifi_ssid,
            authmode=constants.WIFI_AUTHMODES[cfg.wifi_authmode],
            password=cfg.wifi_key,
            dhcp_hostname=cfg.hostname
        )
        wlan.active(True)

    with gpio:
        gpio.off(constants.LED_POWER)

    return wlan


async def ensure_up():
    global wlan

    if cfg.wifi_mode == "ap":
        return

    while True:
        if not wlan.isconnected():
            # Turn off Wi-Fi first
            wlan.active(False)
            await uasyncio.sleep(1)

            up()

        await uasyncio.sleep(1)
