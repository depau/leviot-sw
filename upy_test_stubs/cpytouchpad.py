import os

import utime

mock_tp_dir = "/tmp/cpytouch"


class FakeTouchpad:
    def __init__(self, name, *a):
        self.name = name
        self.event_start = 0

        if not os.path.exists(mock_tp_dir):
            os.mkdir(mock_tp_dir)

        self.fpath = os.path.join(mock_tp_dir, self.name)

    def update(self, action_flag: bool) -> bool:
        if self.event_start == 0 and os.path.exists(self.fpath):
            self.event_start = utime.ticks_ms()
        elif not os.path.exists(self.fpath):
            self.event_start = 0
        return False

    @property
    def acknowledged(self) -> bool:
        return False

    def read(self):
        self.update(False)
        return (
            os.path.exists(self.fpath) and 3 or 0,
            utime.ticks_ms() - self.event_start if os.path.exists(self.fpath) else 0
        )

    def ack(self):
        self.event_start = 0
        os.remove(self.fpath)
