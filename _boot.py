import gc

import uos
from flashbdev import bdev

try:
    if bdev:
        uos.mount(bdev, "/")
except OSError:
    import inisetup

    vfs = inisetup.setup()

gc.collect()

import builtins

import leviot.touchpad
import leviot

# noinspection PyBroadException
try:
    import user_boot
except ImportError:
    pass

# noinspection PyPep8Naming
class Command:
    def __init__(self, callback):
        self.callback = callback

    def __repr__(self):
        self.callback()
        return ""

    def __str__(self):
        self.callback()
        return ""

    def __call__(self):
        self.callback()


def _wifi_up():
    from leviot.network import up
    import uasyncio
    loop = uasyncio.get_event_loop()
    loop.run_until_complete(up())


builtins.run = Command(leviot.main)
builtins.netup = Command(_wifi_up)

try:
    from leviot_conf import autoboot
except ImportError:
    print("Warning: no config file found. Please create 'leviot_conf.py'")
    autoboot = False

if autoboot:
    leviot.main()

print("Type 'run' to re-start the program, 'netup' to turn on and connect to Wi-Fi")
print("You can run your code before startup by adding a 'user_boot.py' script.")
print()
