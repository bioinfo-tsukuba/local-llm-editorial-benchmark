#!/usr/bin/env bash
# Runs the KV-footprint measurement only after the main sweep has finished, so that
# loading and unloading models does not contaminate the sweep's timing numbers.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "ALL TASKS DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] starting KV footprint measurement" | tee -a logs/sweep.log
python3 -u harness/measure_kv.py 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] KV MEASUREMENT DONE" | tee -a logs/sweep.log
