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
source build-venv/bin/activate

echo "Ready to erase: do the following"
echo
echo "- Hold down the BOOT button"
echo "- Press and release the RESET button"
echo "- Release the BOOT button"
echo
read -p "Press Enter when you are ready or Ctrl+C to cancel."

msg "erase flash"
esptool.py --chip esp32 --port "$tty" erase_flash

echo
echo "Now reset the board."