import micropython
import ure
from micropython import const


@micropython.native
def number_to_duration(value: int) -> str:
    hours = str(value // 3600)
    if hours == "0":
        hours = ""
    else:
        hours += "H"
    value %= 3600

    mins = str(value // 60)
    if mins == "0":
        mins = ""
    else:
        mins += "M"
    value %= 60

    secs = str(value) + "S"
    return "PT{}{}{}".format(hours, mins, secs)


@micropython.native
def _parse_next_number(string: str):
    match = ure.match(r"^(\d+\.?\d*)", string)
    if not match:
        raise ValueError("Could not find number in string: {}".format(string))
    needle = match.group(1)
    length = len(needle)
    # I'm intentionally truncating floats
    return int(needle.split(".", 1)[0]), length


_multipliers_date = {
    'Y': const(60 * 60 * 24 * 365),
    'M': const(60 * 60 * 24 * 30),
    'D': const(60 * 60 * 24),
}

_multipliers_time = {
    'H': const(60 * 60),
    'M': const(60),
    'S': const(1),
}


@micropython.native
def duration_to_number(duration: str) -> int:
    if duration[0] != "P":
        raise ValueError("Invalid ISO8601 duration: {}".format(duration))
    duration = duration[1:]
    seconds = 0
    multipliers = _multipliers_date
    while duration:
        if duration[0] == "T":
            duration = duration[1:]
            multipliers = _multipliers_time
            continue
        value, length = _parse_next_number(duration)
        duration = duration[length:]
        try:
            value *= multipliers[duration[0]]
        except KeyError:
            raise ValueError("Invalid multiplier for ISO8601 duration: {}".format(duration[0]))

        duration = duration[1:]
        seconds += value
    return seconds
