import esp32
import micropython
import uasyncio
from machine import Pin, TouchPad
from micropython import const
import usys

from leviot import ulog, constants, conf

log = ulog.Logger("touchpad")


# This is a 1:1 port, with non-necessary stuff removed, of
# https://github.com/espressif/esp-iot-solution/blob/6c8400829886cc0d39b63da5050981244c45870d/components/features/touchpad/touchpad.c
# I also copy-pasted the comments in Chinglish with no changes.
# Some minor changes were made to adapt its state-tracking capabilities
#
# ---
#
# Copyright 2015-2016 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class TouchpadState:
    IDLE = const(0)
    PRESS = const(1)
    RELEASE = const(2)
    PUSH = const(3)


class TPConsts:
    # Period of IIR filter in ms when sensor is not touched.
    FILTER_IDLE_PERIOD = const(100)

    # Period of IIR filter in ms when sensor is being touched. Shouldn't change this value.
    FILTER_TOUCH_PERIOD = const(10)

    # 20ms; Debounce threshold
    STATE_SWITCH_DEBOUNCE = const(20)

    # 5 count number; All channels;
    BASELINE_RESET_COUNT_THRESHOLD = const(5)

    # 800ms; Baseline update cycle
    BASELINE_UPDATE_COUNT_THRESHOLD = const(800)

    # 3% ; Set the low sensitivity threshold. When less than this threshold, remove the jitter processing.
    TOUCH_LOW_SENSE_THRESHOLD = 0.03

    # 75%; This is button type triggering threshold, should be larger than noise threshold. The threshold determines the
    # sensitivity of the touch.
    TOUCH_THRESHOLD_PERCENT = 0.75

    # 20%; The threshold is used to determine whether to update the baseline. The touch system has a signal-to-noise ratio
    # of at least 5:1.
    NOISE_THRESHOLD_PERCENT = 0.20

    # 10%; The threshold prevents frequent triggering.
    HYSTERESIS_THRESHOLD_PERCENT = 0.10

    # 20%; If the touch data exceed this threshold for 'RESET_COUNT_THRESHOLD' times, then reset baseline to raw data.
    BASELINE_RESET_THRESHOLD_PERCENT = 0.20


class FilteredTouchpad:
    def __init__(self, name: str, pin: Pin, sensitivity: float):
        self.name = name
        self.tp = TouchPad(pin)
        self.baseline = 0
        for i in range(3):
            self.baseline += self.tp.read()
        self.baseline /= 3

        self.acknowledged = False

        self.touch_change = sensitivity
        self.sum_ms = 0
        self.state = TouchpadState.IDLE
        self.diff_rate = 0
        self.bl_reset_count = 0
        self.bl_update_count = 0
        self.debounce_count = 0
        self.filter_value = TPConsts.FILTER_TOUCH_PERIOD

        self.serial_thres_sec = 0
        self.serial_interval_ms = 0

        self.touch_thr = self.touch_change * TPConsts.TOUCH_THRESHOLD_PERCENT
        self.noise_thr = self.touch_thr * TPConsts.NOISE_THRESHOLD_PERCENT
        self.hyst_thr = self.touch_thr * TPConsts.HYSTERESIS_THRESHOLD_PERCENT
        self.baseline_reset_thr = self.touch_thr * TPConsts.BASELINE_RESET_THRESHOLD_PERCENT
        self.debounce_thr = TPConsts.STATE_SWITCH_DEBOUNCE // TPConsts.FILTER_TOUCH_PERIOD
        self.bl_reset_count_thr = TPConsts.BASELINE_RESET_COUNT_THRESHOLD
        self.bl_update_count_thr = TPConsts.BASELINE_UPDATE_COUNT_THRESHOLD // TPConsts.FILTER_IDLE_PERIOD

    def read(self) -> tuple:
        return (
            self.state,
            self.sum_ms if self.state in (TouchpadState.PRESS, TouchpadState.PUSH) else 0
        )

    def ack(self) -> None:
        if self.state in (TouchpadState.PUSH, TouchpadState.PRESS):
            self.acknowledged = True

    # Returns updated "action_flag"
    @micropython.native
    def update(self, action_flag: bool) -> bool:
        reading = self.tp.read()
        filtered_reading = self.tp.read_filtered()

        # Use raw data calculate the diff data. Buttons respond fastly™. Frequent button ok.
        diff_data = self.baseline - reading
        self.diff_rate = diff_data / self.baseline

        # IDLE status, wait to be pushed
        if self.state in (TouchpadState.IDLE, TouchpadState.RELEASE):
            self.state = TouchpadState.IDLE

            # If diff data less than noise threshold, update baseline value
            if abs(self.diff_rate) <= self.noise_thr:
                self.bl_reset_count = 0
                self.debounce_count = 0
                self.bl_update_count += 1

                # bl_update_count_th control the baseline update frequency
                if self.bl_update_count > self.bl_update_count_thr:
                    if action_flag is None:
                        # Not exceed action line
                        action_flag = False
                    self.bl_update_count = 0
                    # Baseline updating can use Jitter filter ?
                    self.baseline = filtered_reading
            else:
                # Exceed action line, represent change the filter Interval
                action_flag = True
                self.bl_update_count = 0
                self.debounce_count += 1

                # If the diff data is larger than the touch threshold, touch action be triggered.
                if self.diff_rate >= self.touch_thr + self.hyst_thr:
                    self.bl_reset_count = 0

                    # Debounce processing
                    if self.debounce_count >= self.debounce_thr or self.touch_change < TPConsts.TOUCH_LOW_SENSE_THRESHOLD:
                        self.debounce_count = 0
                        self.state = TouchpadState.PUSH

                # diff data exceed the baseline reset line. reset baseline to raw data.
                elif self.diff_rate <= 0 - self.baseline_reset_thr:
                    self.debounce_count = 0
                    # Check that if do the reset action again. reset baseline value to raw data.
                    self.bl_reset_count += 1
                    if self.bl_reset_count > self.bl_reset_count_thr:
                        self.bl_reset_count = 0
                        self.baseline = reading

                else:
                    self.debounce_count = 0
                    self.bl_reset_count = 0

        # The button is in touched status
        else:
            action_flag = True
            # The button to be pressed continued. long press. # chinglish at its finest
            if self.diff_rate > self.touch_thr - self.hyst_thr:
                # sum_ms is the total time that the read value is under threshold, which means a touch event is on.
                self.sum_ms += self.filter_value
                # whether this is the exact time that a serial event happens
                if self.serial_thres_sec > 0 and self.sum_ms - self.filter_value < self.serial_thres_sec * 1000 <= self.sum_ms:
                    self.state = TouchpadState.PRESS
            # Check the release action
            else:
                # Debounce processing
                self.debounce_count += 1
                if self.debounce_count >= self.debounce_thr or \
                        abs(self.diff_rate) < self.noise_thr or \
                        self.touch_change < TPConsts.TOUCH_LOW_SENSE_THRESHOLD:
                    self.debounce_count = 0
                    self.sum_ms = 0
                    self.state = TouchpadState.RELEASE
                    self.acknowledged = False
        return action_flag


class TouchpadManager:
    def __init__(self):
        self.poll_interval = TPConsts.FILTER_TOUCH_PERIOD
        self.touchpads = set()
        self.running = False
        self.inited = False

    # Must be called after at least one touchpad has been loaded and before starting the loop
    def init(self):
        if len(self.touchpads) == 0:
            raise OSError("Touchpad manager initialized before adding touchpads")
        esp32.touch_filter_start(TPConsts.FILTER_TOUCH_PERIOD)
        self.inited = True

    # noinspection PyShadowingNames
    def load_touchpad(self, name: str, pin: Pin, sensitivity: float = 1) -> FilteredTouchpad:
        if usys.implementation.name == 'micropython':
            tp = FilteredTouchpad(name, pin, sensitivity)
        else:
            import cpytouchpad
            tp = cpytouchpad.FakeTouchpad(name)
        self.touchpads.add(tp)
        return tp

    def set_poll_interval(self, value: int):
        if not self.inited:
            raise OSError("Must be inited first")
        if value == self.poll_interval:
            return
        self.poll_interval = value
        esp32.touch_filter_set_period(value)

    def update(self):
        if not self.inited:
            raise OSError("Must be inited first")

        action_flag = None

        for tp in self.touchpads:
            action_flag = tp.update(action_flag)

        self.set_poll_interval(TPConsts.FILTER_TOUCH_PERIOD if action_flag else TPConsts.FILTER_IDLE_PERIOD)

    async def async_loop(self):
        if not self.inited:
            raise OSError("Must be inited first")

        self.running = True
        while self.running:
            self.update()
            await uasyncio.sleep_ms(self.poll_interval)

    def stop(self):
        self.running = False

    @property
    def active_touchpads(self) -> dict:
        result = {}
        for pad in self.touchpads:
            if pad.acknowledged:
                continue
            state, duration = pad.read()
            if state not in (TouchpadState.PRESS, TouchpadState.RELEASE):
                continue
            result[pad.name] = pad
        return result


touchpad_mgr = TouchpadManager()

for name in constants.TOUCHPADS:
    pin = constants.TOUCHPADS[name]
    sensitivity = conf.touchpads_sensitivity[name]
    touchpad_mgr.load_touchpad(name, Pin(pin), sensitivity)

touchpad_mgr.init()
