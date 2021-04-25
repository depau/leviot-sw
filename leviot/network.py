import network
import uasyncio
import usys

import leviot_conf
from leviot import conf as cfg, constants, ulog
from leviot.extgpio import gpio

wlan = None

log = ulog.Logger("network")


def get_wlan():
    global wlan
    if wlan is None:
        if cfg.wifi_mode == "sta":
            wlan = network.WLAN(network.STA_IF)
        else:
            wlan = network.WLAN(network.AP_IF)
    return wlan


async def up() -> network.WLAN:

    led_on = True
    with gpio:
        gpio.on(constants.LED_POWER)

    wlan = get_wlan()

    if cfg.wifi_mode == "sta":
        while True:
            try:
                if not wlan.active() or not wlan.isconnected():
                    log.i("Connecting to Wi-Fi")
                    wlan.active(True)
                    wlan.config(dhcp_hostname=cfg.hostname)
                    wlan.connect(cfg.wifi_ssid, cfg.wifi_key, listen_interval=leviot_conf.wifi_listen_interval)

                    while not wlan.isconnected():
                        await uasyncio.sleep_ms(250)
                        with gpio:
                            led_on = not led_on
                            gpio.value(constants.LED_POWER, led_on)
                break
            except Exception as e:
                log.e("Failed to connect to Wi-Fi, will retry")
                usys.print_exception(e)
                try:
                    wlan.active(False)
                    await uasyncio.sleep_ms(500)
                except Exception as e:
                    usys.print_exception(e)
                    pass
        log.i("Connected with IP " + wlan.ifconfig()[0])

    elif cfg.wifi_mode == "ap":
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
    wlan = get_wlan()

    if cfg.wifi_mode == "ap":
        return

    while True:
        if not wlan.isconnected():
            # Turn off Wi-Fi first
            wlan.active(False)
            await uasyncio.sleep(1)

            await up()

        await uasyncio.sleep(1)
