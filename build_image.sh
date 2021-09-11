#!/bin/bash
set -e

MPY_VER="a9bbf7083ef6b79cf80bdbf34984d847a6c4aae9"
ESP32_IDF_COMMIT=v4.1.1

function msg() {
  echo -e "[\e[0;92m*\e[0m]" "$@"
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 [board] [--16]"
  echo "Default: GENERIC_OTA"
  echo
  echo "Specify '--16' in order to build with support for 16MB flash chips. Default is 4MB."
  exit
fi

port="esp32"
board="GENERIC_OTA"
flash16=0
extra_make_args=()

if [ -n "$1" ]; then
  board="$1"
fi
if [ "$2" == "--16" ]; then
  flash16=1
fi

if [ $port == "esp8266" ]; then
  msg "Using Docker"
  make=(docker run --rm -v "$PWD/micropython:$PWD/micropython" -u $UID -w "$PWD/micropython" larsks/esp-open-sdk make)

elif [ $port == "esp32" ]; then
  msg "Using local ESP-IDF"

  make=(make)
  export ESPIDF="$PWD/esp-idf"

  if [ ! -d "$ESPIDF" ]; then
    msg "download ESP-IDF"
    git clone https://github.com/espressif/esp-idf.git "$ESPIDF"
    pushd "$ESPIDF"
    git checkout "$ESP32_IDF_COMMIT"
    ./install.sh
    popd
  else
    msg "ESP-IDF found at $PWD/esp-idf"
  fi

  source "$ESPIDF/export.sh"
  extra_make_args=(ESPIDF="$ESPIDF")
fi

cd "$(git rev-parse --show-toplevel)"

if [ ! -e "build-venv/bin/python" ]; then
  msg "(re)create build Python virtual environment"
  rm -Rf build-venv 2>/dev/null
  python3 -m venv build-venv
  source build-venv/bin/activate
  pip install --upgrade pip wheel adafruit-ampy esptool
fi

if [ ! -f "micropython/LICENSE" ]; then
  msg "clone micropython"
  git clone https://github.com/micropython/micropython || true
fi
msg "micropython checkout"
cd micropython
git submodule update --init
git stash && git stash drop || true
git checkout $MPY_VER

if [ ! -f applied-patches.hook ]; then
  for patch in ../mpy-patches/*.patch; do
    git am <"$patch"
  done
fi

touch applied-patches.hook

if [ $flash16 == 1 ]; then
  ## Set 16MB flash size
  sed -i 's/0x200000, 0x200000/0x200000, 0xe00000/g' ports/esp32/partitions.csv
  sed -i 's/0x0f0000/0xcf0000/g' ports/esp32/partitions-ota.csv
  sed -i 's/4MB/16MB/g' ports/esp32/boards/sdkconfig.base
fi

cd ..

cd micropython
msg "micropython submodules"
git submodule update --init --recursive

msg "mpy-cross"
"${make[@]}" -j$(nproc) -C mpy-cross

msg "leviot module"
[ -d "ports/$port/modules/leviot" ] && rm -Rf "ports/$port/modules/leviot"
[ -d "ports/$port/modules/mqtt_as" ] && rm -Rf "ports/$port/modules/mqtt_as"
#[ -d "ports/$port/build-$board/frozen_mpy" ] && rm -Rf "ports/$port/build-$board/frozen_mpy"
# MicroPython > 1.14 broke makefiles and it won't notice changes in modules
[ -d "ports/$port/build-$board" ] && rm -Rf "ports/$port/build-$board"
cp -a ../leviot "ports/$port/modules/leviot"
cp -a ../mqtt_as "ports/$port/modules/mqtt_as"
cp ../_boot.py "ports/$port/modules/"

msg "mpy ports/$port submodules"
"${make[@]}" -j$(nproc) -C "ports/$port" submodules

msg "mpy ports/$port clean"
"${make[@]}" -j$(nproc) -C "ports/$port" clean

msg "mpy ports/$port BOARD=$board " "${extra_make_args[@]}"
"${make[@]}" -j$(nproc) -C "ports/$port" BOARD="$board" "${extra_make_args[@]}"

firmware_path="ports/$port/build-$board"

if [ -f "$firmware_path/firmware-combined.bin" ]; then
  msg "Success! Output firmware: micropython/$firmware_path/firmware-combined.bin"
elif [ -f "$firmware_path/firmware.bin" ]; then
  msg "Success! Output firmware: micropython/$firmware_path/firmware.bin"
else
  msg "Build failed."
fi
