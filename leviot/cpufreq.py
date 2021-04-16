import machine
import micropython

from leviot import conf

_perfcount: int = 0


@micropython.native
def perf():
    global _perfcount
    _perfcount += 1
    if _perfcount > 0:
        machine.freq(conf.cpu_freq_perf)


@micropython.native
def idle():
    global _perfcount
    _perfcount = max(0, _perfcount - 1)
    if _perfcount == 0:
        machine.freq(conf.cpu_freq_idle)


@micropython.native
def fast(func):
    @micropython.native
    def wrapper(*a, **kw):
        perf()
        ret = func(*a, **kw)
        idle()
        return ret

    return wrapper


@micropython.native
def afast(coro):
    async def wrapper(*a, **kw):
        perf()
        ret = await coro(*a, **kw)
        idle()
        return ret

    return wrapper
