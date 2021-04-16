const = lambda x: x

import sys

# Monkey patch built-ins to run in CPython for testing
if sys.implementation.name != 'micropython':
    import builtins

    builtins.const = const


def native(func):
    return func


def viper(func):
    return func
