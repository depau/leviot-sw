from leviot.utils.usyslog import UDPClient as SyslogClient, SyslogClient as DummyClient
from leviot import conf

mqtt = None

def set_mqtt(mqttctrl):
    global mqtt
    mqtt = mqttctrl


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

    def d(self, message):
        self._print_and_mqtt("DEBUG {}: {}".format(self.tag, message))
        self.syslog_reconnect()
        self.syslog.debug("{}: {}".format(self.tag, message))

    def i(self, message):
        self._print_and_mqtt("INFO  {}: {}".format(self.tag, message))
        self.syslog_reconnect()
        self.syslog.info("{}: {}".format(self.tag, message))

    def w(self, message):
        self._print_and_mqtt("WARN  {}: {}".format(self.tag, str(message)))
        self.syslog_reconnect()
        self.syslog.warning("{}: {}".format(self.tag, message))

    def e(self, message):
        self._print_and_mqtt("ERROR {}: {}".format(self.tag, str(message)))
        self.syslog_reconnect()
        self.syslog.error("{}: {}".format(self.tag, message))
