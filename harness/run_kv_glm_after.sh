#!/usr/bin/env bash
# The KV sweep started before the model list was corrected from the (unpullable) hf.co
# tag to the locally imported name, so GLM-4.5-Air is measured separately here.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "SPEED BENCH DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] KV + speed for glm-4.5-air:q4" | tee -a logs/sweep.log
python3 -u harness/measure_kv.py glm-4.5-air:q4 2>&1 | tee -a logs/sweep.log
python3 -u harness/bench_speed.py glm-4.5-air:q4 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] GLM KV/SPEED DONE" | tee -a logs/sweep.log
