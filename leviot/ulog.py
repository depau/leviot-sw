mqtt = None


def set_mqtt(mqttctrl):
    global mqtt
    mqtt = mqttctrl


class Logger:
    def __init__(self, tag):
        self.tag = tag

    @staticmethod
    def _print_and_mqtt(message: str):
        print("$$  " + message)
        if mqtt is not None:
            mqtt.log(message)

    def d(self, message):
        self._print_and_mqtt("DEBUG {}: {}".format(self.tag, message))

    def i(self, message):
        self._print_and_mqtt("INFO  {}: {}".format(self.tag, message))

    def w(self, message):
        self._print_and_mqtt("WARN  {}: {}".format(self.tag, str(message)))

    def e(self, message):
        self._print_and_mqtt("ERROR {}: {}".format(self.tag, str(message)))
