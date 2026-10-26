#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/5] Assembling fizzbuzz.s..."
python3 assembler.py fizzbuzz.s

echo "[2/5] Disassembling ASCII machine code..."
python3 disassembler.py fizzbuzz.mhc-ascii -o reconstructed.s

echo "[3/5] Reassembling reconstructed source..."
python3 assembler.py reconstructed.s \
  --ascii roundtrip.mhc-ascii \
  --bin roundtrip.mhc-bin

echo "[4/5] Comparing original and round-trip binary files..."
cmp fizzbuzz.mhc-bin roundtrip.mhc-bin

echo "[5/5] Generated files:"
ls -lh \
  fizzbuzz.mhc-ascii \
  fizzbuzz.mhc-bin \
  reconstructed.s \
  roundtrip.mhc-ascii \
  roundtrip.mhc-bin

echo "SUCCESS: round-trip machine-code comparison passed."
