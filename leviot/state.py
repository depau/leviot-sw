class StateTracker:
    power = False
    lock = False
    speed = 1
    prev_speed = 1
    timer_left = None
    lights = True
    user_maint = False