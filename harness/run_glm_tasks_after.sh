#!/usr/bin/env bash
# GLM-4.5-Air had to be imported by hand as `glm-4.5-air:q4` (ollama cannot pull sharded
# GGUF), so run_all.sh's model list -- which still names the hf.co tag -- skips it for
# every task. Run the whole task set for it under its real name.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "VARIANT B DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] GLM-4.5-Air: T3/T4/T2" | tee -a logs/sweep.log
python3 -u harness/run_tasks.py --tasks t3refs,t3ja,t4abs,t4ph --models glm-4.5-air:q4 --seeds 42 2>&1 | tee -a logs/sweep.log
python3 -u harness/run_tasks.py --tasks t2 --models glm-4.5-air:q4 --seeds 42 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] GLM TASKS DONE" | tee -a logs/sweep.log
