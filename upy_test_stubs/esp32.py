import datetime
import os
import shelve
import tempfile
import time


def wake_on_touch(flag):
    print(f"Wake on touch: {flag}")


def touch_filter_start(period):
    print(f"touch_filter_start({period})")


def touch_filter_set_period(period):
    print(f"touch_filter_set_period({period})")


class NVS:
    def __init__(self, namespace):
        if len(namespace) > 15:
            raise OSError("NVS namespace key too long")

        self.path = os.path.join(tempfile.gettempdir(), namespace + ".shelve")

        with shelve.open(self.path) as shelf:
            if "current" in shelf:
                self.nvs = shelf["current"]
            else:
                self.nvs = {}
                shelf["current"] = {}

            if "history" not in shelf:
                shelf["history"] = {}

        print(f"Namespace: {namespace} ({self.path})")
        self.ns = namespace
        self.transaction = {}

    def set_i32(self, key, value):
        if len(key) > 15:
            raise OSError("NVS key too long")
        print(f"NVS set i32 [{self.ns}] {key}={value}")
        self.transaction[key] = value
        self.nvs[key] = value

    def get_i32(self, key):
        if len(key) > 15:
            raise OSError("NVS key too long")
        v = self.nvs.get(key, None)
        if v is None:
            raise OSError
        return v

    def commit(self):
        print(f"NVS commit {self.ns}")

        with shelve.open(self.path) as shelf:
            shelf["current"] = self.nvs
            # Required due to the way shelve tracks changes
            history = shelf["history"]
            history[datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")] = self.transaction
            shelf["history"] = history
            self.transaction = {}
