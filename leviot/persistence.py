import esp32
import usys
from utime import time

from leviot import ulog
from leviot.state import state_tracker

log = ulog.Logger("persistence")

# 5x 32bit values are stored into NVS and 3 of them are updated on average every minute. Considering 10.000 erase
# cycles per flash sector (512 bytes), 125 entries per sector (NVS page) and 32 pages (48 if not building without OTA
# support), that's 40.000.000 times we can write one value.
# For 3 value every minute we reach this threshold after 25 years. This could improve if we add support for 64 bit
# values in MicroPython's NVS API, bringing this up to 38 years (2 values every minute).
#
# Considering that this only happens only when the air purifier is actually running and that when it is, a fan is
# blowing (which effectively cools down the ESP32 chip and extends the flash lifetime, this could be even longer.

DEVICE_NAMESPACE = "LevIoT"

## Device lifetime in seconds
DEVICE_LIFETIME = "Lifetime"

## Setting bits
DEVICE_SETTINGS = "Settings"

BIT_SPEED = 0
BIT_PREV_SPEED = 2
BIT_POWER = 4
BIT_LIGHTS = 5
BIT_LOCK = 6
BIT_USERMAINT = 7
# Bits from 8 to 12 are reserved for later use
# Timer is 16 bits, in minutes, ~45 days is more than enough
BIT_TIMER_LEFT = 16

BMASK_SPEED = 0b11
BMASK_TIMER_LEFT = 0xffff

# Unfortunately none of the values below are able to fit within 16 bits in meaningful ways,
# so we have to use an entire 32 bit slot for each value.
# We can therefore write the time in seconds, there's enough space for that.
# Hopefully MicroPython will add support for 64bit ints for NVS.

# Relative to lifetime, written only on filter replacement
FILTER_INSTALL_TIME = "FilterInstTime"

# Last filter dusting time relative to maintenance time
FILTER_LAST_DUST = "LastDustTime"

# Time for maintenance purposes relative to fan speed, 1 sec @ max speed == 1, 1 sec @ min speed = 1/4
FILTER_RELATIVE_LIFETIME = "FilterRelLftime"

## Constants

# Time to wait between the last user action before persisting the data, to avoid wearing the SPI flash for nothing
USER_ACTION_TIMEOUT_SEC = 5
# Interval for updating the device's powered-on lifetime and filter maintenance time, as well as the timer left if
# enabled
LIFETIME_UPDATE_INTERVAL_SEC = 60 * 1

# Every 4 weeks if used 12h per day at max speed
DUST_TIMEOUT = 60 * 60 * 12 * 7 * 4

# Every 6 months if used 12h per day at max speed
REPLACE_TIMEOUT = 60 * 60 * 12 * 30 * 6


class Persistence:
    def __init__(self):
        self.nvs = esp32.NVS(DEVICE_NAMESPACE)
        self.last_update = time()
        self.last_dust = 0
        self.filter_install = 0
        self._prev_settings = 0
        self._lifetime = 0
        self._relative_filter_lifetime = 0
        self._last_persist_settings_time = time() - USER_ACTION_TIMEOUT_SEC
        self._last_not_presisted_settings = 0

        loaded = 0

        try:
            _settings = self.nvs.get_i32(DEVICE_SETTINGS)
            state_tracker.power = (_settings >> BIT_POWER) & 1 == 1
            state_tracker.speed = (_settings >> BIT_SPEED) & BMASK_SPEED
            state_tracker.prev_speed = (_settings >> BIT_PREV_SPEED) & BMASK_SPEED
            state_tracker.lights = (_settings >> BIT_LIGHTS) & 1 == 1
            state_tracker.lock = (_settings >> BIT_LOCK) & 1 == 1
            state_tracker.user_maint = (_settings >> BIT_USERMAINT) & 1 == 1
            state_tracker.timer_left = (_settings >> BIT_TIMER_LEFT) & BMASK_TIMER_LEFT
            loaded += 1
        except OSError as e:
            usys.print_exception(e)

        try:
            self._lifetime = self.nvs.get_i32(DEVICE_LIFETIME)
            loaded += 1
        except OSError as e:
            usys.print_exception(e)

        try:
            self._relative_filter_lifetime = self.nvs.get_i32(FILTER_RELATIVE_LIFETIME)
            loaded += 1
        except OSError as e:
            usys.print_exception(e)

        try:
            self.filter_install = self.nvs.get_i32(FILTER_INSTALL_TIME)
            loaded += 1
        except OSError as e:
            usys.print_exception(e)

        if loaded == 4:
            log.i("Loaded persisted info from storage")
        else:
            if self._relative_filter_lifetime == 0:
                self._relative_filter_lifetime = self.lifetime
            if self.filter_install == 0:
                self.filter_install = self.lifetime
            self.nvs.set_i32(FILTER_INSTALL_TIME, self.filter_install)
            self.nvs.set_i32(FILTER_LAST_DUST, self.last_dust)
            self._persist_settings()
            self._persist_lifetime()
            self._commit()

        if loaded == 0:
            log.i("Created new persistence storage")
        elif loaded < 4:
            log.i("Restored missing values to defaults")

        log.i("Stats:")
        log.i(" - Lifetime: {} seconds".format(self.lifetime))
        log.i(" - Filter installated at {} seconds".format(self.filter_install))
        log.i(" - Filter relative lifetime: {} (NOT seconds)".format(self.relative_filter_lifetime))
        log.i(" - Last dust at {} rel lifetime".format(self.last_dust))
        log.i("Settings:")
        log.i(" - Power: {}".format(state_tracker.power and "on" or "off"))
        log.i(" - Lights: {}".format(state_tracker.lights and "on" or "off"))
        log.i(" - Lock: {}".format(state_tracker.lock and "on" or "off"))
        log.i(" - Speed: {}".format(state_tracker.speed))
        log.i(" - Prev speed: {}".format(state_tracker.prev_speed))
        log.i(" - Timer left: {} minutes".format(state_tracker.timer_left))
        log.i(" - User maintenance reminder: {}".format(state_tracker.user_maint))

    def _persist_settings(self) -> bool:
        _settings = 0
        _settings |= 1 << BIT_POWER if state_tracker.power else 0
        _settings |= 1 << BIT_LIGHTS if state_tracker.lights else 0
        _settings |= 1 << BIT_LOCK if state_tracker.lock else 0
        _settings |= 1 << BIT_USERMAINT if state_tracker.user_maint else 0
        _settings |= (state_tracker.speed & BMASK_SPEED) << BIT_SPEED
        _settings |= (state_tracker.prev_speed & BMASK_SPEED) << BIT_PREV_SPEED
        _settings |= ((state_tracker.timer_left & BMASK_TIMER_LEFT) << BIT_TIMER_LEFT) if state_tracker.timer_left else 0

        if _settings != self._prev_settings:
            # Do not commit if user is having fun with buttons
            if time() - self._last_persist_settings_time < USER_ACTION_TIMEOUT_SEC:
                if _settings != self._last_not_presisted_settings:
                    self._last_persist_settings_time = time()
                self._last_not_presisted_settings = _settings
                return False

            self._last_persist_settings_time = time()
            self.nvs.set_i32(DEVICE_SETTINGS, _settings)
            self._prev_settings = _settings
            return True
        return False

    def _persist_lifetime(self):
        self._lifetime += time() - self.last_update
        self._relative_filter_lifetime += self._time_to_rel_time(time() - self.last_update, state_tracker.speed)
        self.last_update = time()

        self.nvs.set_i32(DEVICE_LIFETIME, self.lifetime)
        self.nvs.set_i32(FILTER_RELATIVE_LIFETIME, self._lifetime)

    def _commit(self):
        log.d("Commit persistence storage")
        self.nvs.commit()

    @property
    def lifetime(self):
        return (time() - self.last_update) + self._lifetime

    @property
    def relative_filter_lifetime(self):
        return self._time_to_rel_time(time() - self.last_update, state_tracker.speed) + self._relative_filter_lifetime

    # noinspection PyShadowingNames
    @staticmethod
    def _time_to_rel_time(time, speed):
        return int(time / (4 - speed))

    @property
    def dusting_due(self) -> bool:
        return self.relative_filter_lifetime - self.last_dust > DUST_TIMEOUT

    @property
    def replacement_due(self) -> bool:
        return self.relative_filter_lifetime > REPLACE_TIMEOUT

    def notify_poweron(self):
        self.last_update = time()

    def notify_maintenance(self):
        state_tracker.user_maint = False
        if self.replacement_due:
            self._persist_lifetime()
            self.last_dust = 0
            self.filter_install = self.lifetime
            self.nvs.set_i32(FILTER_INSTALL_TIME, self.filter_install)
            self.nvs.set_i32(FILTER_LAST_DUST, self.last_dust)
            self._relative_filter_lifetime = 0
            self._persist_lifetime()
        else:
            self.last_dust = self.relative_filter_lifetime

        self._commit()

    def notify_poweroff(self):
        self._persist_settings()
        self._persist_lifetime()
        self._commit()

    # This is async so it can be scheduled in the asyncio event loop
    async def track(self):
        changed = self._persist_settings()
        if state_tracker.power:
            delta = time() - self.last_update
            if delta >= LIFETIME_UPDATE_INTERVAL_SEC:
                self._persist_lifetime()
                changed = True
        if changed:
            self._commit()


persistence = Persistence()
