#!/bin/bash

function msg() {
  echo -e "[\e[0;92m*\e[0m]" "$@"
}

if [ "$1" == "" ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 /dev/ttySERIAL_PORT [board]"
  echo "Default board: GENERIC_OTA"
  exit 1
fi

board="GENERIC_OTA"
tty="$1"
build_venv="build-venv"
if ! [ "$2" == "" ]; then
	build_venv="$2"
fi

if [ ! -e "$tty" ]; then
  echo "Serial port does not exist"
  exit 1
fi

if [ ! -e "$build_venv/bin/python" ]; then
  echo "Build virtual environment does not exist or is broken. Run ./build_image.sh first to set it up."
  exit 1
fi
source $build_venv/bin/activate

fw_path="micropython/ports/esp32/build-$board/firmware.bin"
if [ ! -f "$fw_path" ]; then
  echo "Could not find built firmware. Run ./build_image.sh to build it first."
  exit 1
fi

echo "Ready to flash: do the following"
echo
echo "- Hold down the BOOT button"
echo "- Press and release the RESET button"
echo "- Release the BOOT button"
echo
read -p "Press Enter when you are ready or Ctrl+C to cancel."

msg "flash image"
esptool.py --chip esp32 --port "$tty" --baud 921600 write_flash -z --flash_mode dio --flash_freq 40m 0x1000 "$fw_path"

echo
echo "Now reset the board."
