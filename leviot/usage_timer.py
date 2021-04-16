from utime import time

import esp32

from leviot.state import StateTracker

NAMESPACE = "leviot_filter"
ON_TIME = "on_time"
LAST_REPLACE = "last_replace"
LAST_DUST = "last_dust"

MIN_UPDATE_INTERVAL_SEC = 60 * 5

# Every 4 weeks if used 12h per day
DUST_TIMEOUT = 60 * 60 * 12 * 7 * 4

# Every 6 months if used 12h per day
REPLACE_TIMEOUT = 60 * 60 * 12 * 30 * 6


class UsageTimer:

    def __init__(self):
        self.nvs = esp32.NVS(NAMESPACE)
        self.last_update = time()

        try:
            self._on_time = self.nvs.get_i32(ON_TIME)
            self.last_replace = self.nvs.get_i32(LAST_REPLACE)
            self.last_dust = self.nvs.get_i32(LAST_DUST)
        except OSError:
            self._on_time = 0
            self.last_replace = 0
            self.last_dust = 0
            self.nvs.set_i32(ON_TIME, 0)
            self.nvs.set_i32(LAST_REPLACE, 0)
            self.nvs.set_i32(LAST_DUST, 0)
            self.nvs.commit()

    @property
    def on_time(self):
        return (time() - self.last_update) + self._on_time

    @property
    def dusting_due(self) -> bool:
        return self.on_time - self.last_dust > DUST_TIMEOUT

    @property
    def replacement_due(self) -> bool:
        return self.on_time - self.last_replace > REPLACE_TIMEOUT

    def notify_poweron(self):
        self.last_update = time()

    def persist(self):
        self._on_time += time() - self.last_update
        self.last_update = time()
        self.nvs.set_i32(ON_TIME, self._on_time)
        self.nvs.commit()

    def notify_maintenance(self):
        self.last_dust = self.on_time
        self.nvs.set_i32(LAST_DUST, self.last_dust)

        if self.replacement_due:
            self.last_replace = self.on_time
            self.nvs.set_i32(LAST_REPLACE, self.last_replace)

        self.nvs.commit()

    def notify_poweroff(self):
        self.persist()

    async def track(self):
        # This is async so it can be scheduled in the asyncio event loop
        if not StateTracker.power:
            return
        delta = time() - self.last_update
        if delta < MIN_UPDATE_INTERVAL_SEC:
            return
        self.persist()


usage = UsageTimer()
