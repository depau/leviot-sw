AUTH_OPEN = "AUTH_OPEN"
AUTH_WEP = "AUTH_WEP"
AUTH_WPA_PSK = "AUTH_WPA_PSK"
AUTH_WPA2_PSK = "AUTH_WPA2_PSK"
AUTH_WPA_WPA2_PSK = "AUTH_WPA_WPA2_PSK"

STA_IF = "STA_IF"
AP_IF = "AP_IF"


class WLAN:
    def __init__(self, *args):
        print(f"STUB network.WIFI create{args}")
        self.args = args
        self.conncheck_count = 0

    def active(self, active=True):
        print(f"STUB network.WIFI.active({active})")
        return active

    def config(self, **kwargs):
        print(f"STUB network.WIFI.config({kwargs})")

    def connect(self, ssid, psk, *a, **kw):
        print(f"STUB network.WIFI.connect('{ssid}', '{psk}')")

    def isconnected(self):
        self.conncheck_count += 1
        return self.conncheck_count > 10

    def scan(self):
        print(f"STUB network.WIFI.scan()")

    def ifconfig(self, *a, **kw):
        return "192.168.1.2", "255.255.255.0", "192.168.1.1", "192.168.1.1"
