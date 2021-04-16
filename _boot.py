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

import leviot

# noinspection PyBroadException
try:
    import user_boot
except:
    pass


# noinspection PyPep8Naming
class Run:
    def __repr__(self):
        leviot.main()
        return ""

    def __str__(self):
        leviot.main()
        return ""

    def __call__(self):
        leviot.main()


builtins.run = Run()

try:
    from leviot_conf import autoboot
except ImportError:
    print("Warning: no config file found. Please create 'leviot_conf.py'")
    autoboot = False

if autoboot:
    leviot.main()

print("Type 'run' to re-start the program.")
print("You can run your code before startup by adding a 'user_boot.py' script.")
print()
