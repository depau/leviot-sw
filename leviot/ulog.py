from leviot.utils.usyslog import UDPClient as SyslogClient, SyslogClient as DummyClient
from leviot import conf

mqtt = None

def set_mqtt(mqttctrl):
    global mqtt
    mqtt = mqttctrl


try:
    try:
        import uio as io
        import usys as sys
    except ImportError:
        import io
        import sys
except ImportError:
    print("SKIP")
    raise SystemExit

if hasattr(sys, "print_exception"):
    print_exception = sys.print_exception
else:
    import traceback

    print_exception = lambda e, f: traceback.print_exception(None, e, sys.exc_info()[2], file=f)


def exception_value(e):
    if isinstance(e, Exception):
        buf = io.StringIO()
        print_exception(e, buf)
        return buf.getvalue()
    else:
        return e


class Logger:
    def __init__(self, tag):
        self.tag = tag
        self.syslog = DummyClient()

    @staticmethod
    def _print_and_mqtt(message: str):
        print("$$  " + message)
        if mqtt is not None:
            mqtt.log(message)

    def syslog_reconnect(self):
        if not conf.syslog or type(self.syslog) is SyslogClient:
            return

        try:
            self.syslog = SyslogClient(ip=conf.syslog)
            self._print_and_mqtt("Syslog Connected at {}".format(conf.syslog))
        except:
            self._print_and_mqtt("DEBUG: Cannot connect to {} SysLog server".format(conf.syslog))

    def d(self, m):
        message = exception_value(m)
        self._print_and_mqtt("DEBUG {}: {}".format(self.tag, message))
        try:
            self.syslog_reconnect()
            self.syslog.debug("{}: {}".format(self.tag, message))
        except:
            self.syslog = DummyClient()

    def i(self, m):
        message = exception_value(m)
        self._print_and_mqtt("INFO  {}: {}".format(self.tag, message))
        try:
            self.syslog_reconnect()
            self.syslog.info("{}: {}".format(self.tag, message))
        except:
            self.syslog = DummyClient()


    def w(self, m):
        message = exception_value(m)
        self._print_and_mqtt("WARN  {}: {}".format(self.tag, str(message)))
        try:
            self.syslog_reconnect()
            self.syslog.warning("{}: {}".format(self.tag, message))
        except:
            self.syslog = DummyClient()

    def e(self, m):
        message = exception_value(m)
        self._print_and_mqtt("ERROR {}: {}".format(self.tag, str(message)))
        try:
            self.syslog_reconnect()
            self.syslog.error("{}: {}".format(self.tag, message))
        except:
            self.syslog = DummyClient()