#!/usr/bin/env bash
# Build and run the complete test suite (C++ unit tests, firmware host check,
# Python integration tests).
set -euo pipefail
cd "$(dirname "$0")/.."
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build build -j"$(nproc 2>/dev/null || echo 2)" >/dev/null
echo "== C++ unit tests"; ./build/unit_tests
echo "== firmware host check"; ./build/firmware_host_check
echo "== firmware host check (R2)"; ./build/firmware_host_check_r2
echo "== firmware host check (R3)"; ./build/firmware_host_check_r3
echo "== Python integration tests"; python3 -m unittest discover -s tests -v
