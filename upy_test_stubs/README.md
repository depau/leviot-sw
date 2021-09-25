# MicroPython CPython stubs

This directory contains fake implementations of MicroPython-specific APIs to run the program with CPython and test
functionality without flashing it on an actual ESP32.

Only APIs that are actually in use are stubbed.

To run the program with CPython, run from the main project directory:

```bash
PYTHONPATH="$(pwd):$(pwd)/upy_test_stubs" python _boot.py
```

All listening ports are automatically offset by 8000 if they're lower than 1024. So if `http_listen_port` is set to 80,
it will listen on 8080 on CPython.

## License

These stubs are licensed under the GNU Lesser General Public License v3.0.

Feel free to copy anything you want from here to your project, as long as it's licensed under a GPL-compatible license
or as long as you redistribute the changes to this source code.
