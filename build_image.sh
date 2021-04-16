#!/bin/bash
set -e

MPY_VER="a9bbf7083ef6b79cf80bdbf34984d847a6c4aae9"
ESP32_IDF_COMMIT=v4.1.1

function msg() {
  echo -e "[\e[0;92m*\e[0m] $1"
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "Usage: $0 [port] [board]"
  echo "Default: esp32 GENERIC_OTA"
  echo "ESP8266 is not supported by the code, so even though this scripts technically"
  echo "can build ESP8266 images, it won't work."
  echo
  echo "This script assumes a 16MB flash. If that's not what you have, edit it."
  exit
fi

port="esp32"
board="GENERIC_OTA"
extra_make_args=()

if [ -n "$1" ]; then
  port="$1"
fi
if [ -n "$2" ]; then
  board="$2"
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

if [ ! -f "micropython/LICENSE" ]; then
  msg "clone micropython"
  git clone --recursive https://github.com/micropython/micropython || true
fi
msg "micropython checkout"
cd micropython
git stash && git stash drop || true
git checkout $MPY_VER
git am << EOF
From 32c0a13ee62ceea4eae465799403af9b62563e10 Mon Sep 17 00:00:00 2001
From: Davide Depau <davide@depau.eu>
Date: Fri, 16 Apr 2021 00:44:55 +0200
Subject: [PATCH] Update board name

---
 ports/esp32/boards/GENERIC/mpconfigboard.h     | 2 +-
 ports/esp32/boards/GENERIC_OTA/mpconfigboard.h | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)

diff --git a/ports/esp32/boards/GENERIC/mpconfigboard.h b/ports/esp32/boards/GENERIC/mpconfigboard.h
index 644807f78..4445b946e 100644
--- a/ports/esp32/boards/GENERIC/mpconfigboard.h
+++ b/ports/esp32/boards/GENERIC/mpconfigboard.h
@@ -1,2 +1,2 @@
-#define MICROPY_HW_BOARD_NAME "ESP32 module"
+#define MICROPY_HW_BOARD_NAME "LevIoT"
 #define MICROPY_HW_MCU_NAME "ESP32"
diff --git a/ports/esp32/boards/GENERIC_OTA/mpconfigboard.h b/ports/esp32/boards/GENERIC_OTA/mpconfigboard.h
index ff39c4b2b..d000d217a 100644
--- a/ports/esp32/boards/GENERIC_OTA/mpconfigboard.h
+++ b/ports/esp32/boards/GENERIC_OTA/mpconfigboard.h
@@ -1,2 +1,2 @@
-#define MICROPY_HW_BOARD_NAME "4MB/OTA module"
+#define MICROPY_HW_BOARD_NAME "LevIoT (with OTA)"
 #define MICROPY_HW_MCU_NAME "ESP32"
--
2.31.1
EOF

## Set 16MB flash size
#sed -i 's/0x200000, 0x200000/0x200000, 0xe00000/g' ports/esp32/partitions.csv
#sed -i 's/0x0f0000/0xcf0000/g' ports/esp32/partitions-ota.csv
#sed -i 's/4MB/16MB/g' ports/esp32/boards/sdkconfig.base
cd ..


cd micropython
msg "micropython submodules"
git submodule update --init --recursive

msg "mpy-cross"
"${make[@]}" -j$(nproc) -C mpy-cross

msg "leviot module"
[ -d "ports/$port/modules/leviot" ] && rm -Rf "ports/$port/modules/leviot"
#[ -d "ports/$port/build-$board/frozen_mpy" ] && rm -Rf "ports/$port/build-$board/frozen_mpy"
# MicroPython > 1.14 broke makefiles and it won't notice changes in modules
[ -d "ports/$port/build-$board" ] && rm -Rf "ports/$port/build-$board"
cp -a ../leviot "ports/$port/modules/leviot"
cp -a ../mqtt_as "ports/$port/modules/mqtt_as"

msg "mpy ports/$port submodules"
"${make[@]}" -j$(nproc) -C "ports/$port" submodules

msg "mpy ports/$port clean"
"${make[@]}" -j$(nproc) -C "ports/$port" clean

msg "mpy ports/$port BOARD=$board ${extra_make_args[@]}"
"${make[@]}" -j$(nproc) -C "ports/$port" BOARD="$board" "${extra_make_args[@]}"

firmware_path="ports/$port/build-$board"

if [ -f "$firmware_path/firmware-combined.bin" ]; then
  msg "Success! Output firmware: micropython/$firmware_path/firmware-combined.bin"
elif [ -f "$firmware_path/firmware.bin" ]; then
  msg "Success! Output firmware: micropython/$firmware_path/firmware.bin"
else
  msg "Build failed."
fi
