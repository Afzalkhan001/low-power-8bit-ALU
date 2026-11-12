#!/usr/bin/env sh
# One-click setup check for the Low-Power 8-Bit ALU project (Linux / macOS).
# Run:  sh run_checks.sh
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "Python 3 was not found. Install it (for example: sudo apt install python3) and run again."
  exit 1
fi
echo "Using $($PY --version 2>&1)"
echo

fail() { echo; echo "A CHECK FAILED - read the message above. See Troubleshooting in SETUP.md."; exit 1; }

echo "[1/5] Gate-level check: 16 ops x 65,536 input pairs (about 20 seconds)..."
$PY model/alu_model.py || fail
echo
echo "[2/5] Generating the Spectre netlists..."
$PY virtuoso/gen_netlist.py "$@" || fail
echo
echo "[3/5] Transistor netlist check (switch level)..."
$PY virtuoso/switch_sim.py > /tmp/alu8_switch.txt || { cat /tmp/alu8_switch.txt; fail; }
grep "SWITCH-LEVEL RESULT" /tmp/alu8_switch.txt
echo
echo "[4/5] Building the website..."
$PY simulator/build_sim.py || fail
$PY website/build_site.py || fail
echo
echo "[5/5] Website engine check (needs Node.js, optional)..."
if command -v node >/dev/null 2>&1; then node simulator/test_engine.js || fail
else echo "Node.js not installed - skipped. This check is optional."; fi

echo
echo "=============================================="
echo " ALL CHECKS PASSED"
echo "=============================================="
echo "Open website/index.html in a browser."
echo "On the Cadence machine, pass your PDK to step 2, for example:"
echo "  sh run_checks.sh --model-file /path/to/gpdk045/models/spectre/gpdk045.scs --section tt"
