from time import *

_time = time


def time():
    return int(_time())

def time_ns():
    return int(_time() * (1000 ** 3))

def sleep_ms(val):
    sleep(val / 1000.)


def ticks_ms():
    return int(_time() * 1000)


def ticks_us():
    return int(_time() * 1000000)


def ticks_diff(t1, t2):
    return t1 - t2
