class Logger:
    def __init__(self, tag):
        self.tag = tag

    def d(self, message):
        print("$$  DEBUG {}: {}".format(self.tag, message))

    def i(self, message):
        print("$$  INFO  {}: {}".format(self.tag, message))

    def w(self, message):
        print("$$  WARN  {}: {}".format(self.tag, str(message)))

    def e(self, message):
        print("$$  ERROR {}: {}".format(self.tag, str(message)))
