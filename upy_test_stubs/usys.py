from sys import *

import traceback


def print_exception(e):
    try:
        traceback.print_exc(e)
    except TypeError:
        print(e)
