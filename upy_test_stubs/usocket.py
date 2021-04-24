import socket as socket_module
from socket import *

_socket_orig = socket


# noinspection PyPep8Naming
class socket(_socket_orig):
    def write(self, buffer):
        if isinstance(buffer, str):
            buffer = buffer.encode()
        return self.send(buffer)

    def read(self, bufsize):
        return self.recv(bufsize)


socket_module.socket = socket
