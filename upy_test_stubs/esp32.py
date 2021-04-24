import os
import shelve
import tempfile
import time


def wake_on_touch(flag):
    print(f"Wake on touch: {flag}")


class NVS:
    def __init__(self, namespace):
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
        print(f"NVS set i32 [{self.ns}] {key}={value}")
        self.transaction[key] = value
        self.nvs[key] = value

    def get_i32(self, key):
        v = self.nvs.get(key, None)
        if v is None:
            raise OSError
        return v

    def commit(self):
        print(f"NVS commit {self.ns}")

        with shelve.open(self.path) as shelf:
            shelf["current"] = self.nvs
            shelf["history"][time.time()] = self.transaction
            self.transaction = {}
