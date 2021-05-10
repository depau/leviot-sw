from leviot import ulog

log = ulog.Logger("state")


class StateTracker:
    def __init__(self):
        self.power = False
        self.lock = False
        self.speed = 1
        self.prev_speed = 1
        self.lights = True
        self.user_maint = False
        self._timer_left = 0

    @property
    def timer_left(self):
        return self._timer_left > 0 and self.timer_left or 0

    @timer_left.setter
    def timer_left(self, value):
        if value < 0:
            try:
                # Trick to print stack trace
                raise ValueError()
            except ValueError as e:
                log.e("Provided value for timer_left is < 0, which is invalid!")
                usys.print_exception(e)
            value = 0
        self._timer_left = 0


state_tracker = StateTracker()
