def wake_on_touch(flag):
    print(f"Wake on touch: {flag}")


class NVS:
    def __init__(self, namespace):
        print(f"Namespace: {namespace}")
        self.ns = namespace
        self.nvs = {}

    def set_i32(self, key, value):
        print(f"NVS set i32 [{self.ns}] {key}={value}")
        self.nvs[key] = value

    def get_i32(self, key):
        v = self.nvs.get(key, None)
        if v is None:
            raise OSError

    def commit(self):
        print(f"NVS commit {self.ns}")
