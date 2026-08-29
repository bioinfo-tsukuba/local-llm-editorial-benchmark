#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
while ! grep -q "KV MEASUREMENT DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] starting cold-cache speed benchmark" | tee -a logs/sweep.log
python3 -u harness/bench_speed.py 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] SPEED BENCH DONE" | tee -a logs/sweep.log
