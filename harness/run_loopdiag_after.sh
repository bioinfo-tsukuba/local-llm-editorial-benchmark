#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
while ! grep -q "T2 RERUN DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] loop diagnosis for cells that returned nothing" | tee -a logs/sweep.log
python3 -u harness/diagnose_loop.py qwen3.5:35b-a3b-bf16 MS-B 32768 2>&1 | tee -a logs/sweep.log
python3 -u harness/diagnose_loop.py qwen3.5:122b-a10b-q4_K_M MS-B 32768 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] LOOP DIAG DONE" | tee -a logs/sweep.log
