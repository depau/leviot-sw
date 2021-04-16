import sys

# Monkey patch built-ins to run in CPython for testing
if sys.implementation.name != 'micropython':
    import builtins

    builtins.const = lambda x: x

from binascii import b2a_base64
from leviot_conf import *

from mqtt_as import config as _mqtt_config_orig

_mqtt_config_orig.update(mqtt_config)
mqtt_config = _mqtt_config_orig

try:
    http_basic_auth = "Basic " + b2a_base64(http_basic_auth.encode()).decode().strip()
except (NameError, AttributeError, ValueError):
    pass
