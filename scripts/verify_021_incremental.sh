#!/bin/bash
# Verify the 021 incremental update tests.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="C:/Users/MW/.conda/envs/pairusdt/python.exe"
TEST_FILE="$(find "$ROOT_DIR" -type f -path '*/01_pairUSDT/test_021_altCycleAnalysisUsdt.py' | head -n 1)"

echo ""
echo "========================================"
echo " Verify 021 incremental update"
echo "========================================"

echo ""
echo "[1/3] Check files"

FILES=(
  ".github/workflows/pipeline-analyze.yml"
  ".github/workflows/pipeline-predict.yml"
  "requirements_action_analyze.txt"
  "requirements_action_predict.txt"
  "01_pairUSDT/021_altCycleAnalysisUsdt.py"
)

ALL_OK=true
for FILE in "${FILES[@]}"; do
  if [ -f "$ROOT_DIR/$FILE" ]; then
    echo "  OK $FILE"
  else
    echo "  MISSING $FILE"
    ALL_OK=false
  fi
done

if [ -z "$TEST_FILE" ]; then
  echo "  MISSING 01_pairUSDT/test_021_altCycleAnalysisUsdt.py under the unit test folder"
  ALL_OK=false
else
  echo "  OK $TEST_FILE"
fi

if [ "$ALL_OK" = false ]; then
  echo "Missing required files."
  exit 1
fi

echo ""
echo "[2/3] Run unit tests"

cd "$ROOT_DIR"
"$PYTHON" -m pytest "$TEST_FILE" -v

echo ""
echo "[3/3] Measure coverage"

"$PYTHON" -m pytest "$TEST_FILE" \
  --cov=021_altCycleAnalysisUsdt \
  --cov-report=term-missing \
  -q

echo ""
echo "Verification complete"
