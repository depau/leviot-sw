#!/bin/bash

function msg() {
  echo -e "[\e[0;92m*\e[0m]" "$@"
}

if [ "$1" == "" ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 /dev/ttySERIAL_PORT"
  exit 1
fi

tty="$1"

if [ ! -e "$tty" ]; then
  echo "Serial port does not exist"
  exit 1
fi

if [ ! -e "build-venv/bin/python" ]; then
  echo "Build virtual environment does not exist or is broken. Run ./build_image.sh first to set it up."
  exit 1
fi

if [ ! -f leviot_conf.py ]; then
  echo "Config file does not exist. Copy leviot_conf.py.template to leviot_conf.py and change it as needed."
  exit 1
fi

if ! PYTHONPATH="$(pwd)/upy_test_stubs" python -c 'import leviot_conf'; then
  echo "Config file is invalid".
  exit 1
fi

source build-venv/bin/activate

echo "Ready to copy: reset the board and, when all LEDs turn on,"
echo "hold the BOOT button until they turn off and the red LED turns on."
echo
read -p "Press Enter when you are ready or Ctrl+C to cancel."

msg "Copying config file to the device"
ampy -p "$tty" -b 115200 put leviot_conf.py

if [ -f "user_boot.py" ]; then
  msg "Copying user boot script"
  ampy -p "$tty" -b 115200 put user_boot.py
fi

msg "Resetting board"
ampy -p "$tty" -b 115200 reset --hard >/dev/null
