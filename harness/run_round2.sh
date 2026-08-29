#!/usr/bin/env bash
# Round 2: (a) T8 tool-calling on the existing tool-capable models, then
# (b) the full task suite on the newly pulled models, then (c) T8 on those too.
# Runs strictly sequentially: memory measurements are invalid with two models resident.
set -u
cd /home/dgx1/projects/2026/test-local-llm
LOG=logs/sweep.log
say(){ echo "=== [$(date -Is)] $*" | tee -a "$LOG"; }

OLD_TOOLS="qwen3.6:35b-a3b-q8_0,qwen3.6:35b-a3b-q4_K_M,gpt-oss:120b,qwen3.5:122b-a10b-q4_K_M"
say "T8 tool-calling on existing models"
python3 -u harness/run_t8.py --models "$OLD_TOOLS" --seeds 42 2>&1 | tee -a "$LOG"

say "waiting for round-2 downloads"
while ! grep -q "ROUND2 PULL DONE" logs/pull_round2.log 2>/dev/null; do sleep 60; done
say "round-2 downloads complete"
ollama list | tee -a "$LOG"

NEW="qwen3.8:27b,qwen3.6:27b,gemma4,nemotron,command-r-plus,llama4:scout"
say "round-2 T1 (both prompt variants)"
python3 -u harness/run_t1.py --models "$NEW" --manuscripts MS-A,MS-B --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_t1.py --models "$NEW" --manuscripts MS-A,MS-B --seeds 42 --variant b 2>&1 | tee -a "$LOG"

say "round-2 T3/T4/T6/T7"
python3 -u harness/run_tasks.py --tasks t3refs,t3ja,t4abs,t4ph,t6c,t6d,t7 --models "$NEW" --seeds 42 2>&1 | tee -a "$LOG"

say "round-2 T2 (131k context)"
python3 -u harness/run_tasks.py --tasks t2 --models "$NEW" --seeds 42 2>&1 | tee -a "$LOG"

say "round-2 T8 tool-calling"
python3 -u harness/run_t8.py --models "$NEW" --seeds 42 2>&1 | tee -a "$LOG"

say "round-2 T5 vision"
.venv/bin/python -u harness/run_t5.py --models qwen3.8:27b,gemma4 --seeds 42 2>&1 | tee -a "$LOG"

say "round-2 memory and speed"
python3 -u harness/measure_kv.py qwen3.8:27b qwen3.6:27b gemma4 nemotron command-r-plus llama4:scout 2>&1 | tee -a "$LOG"
python3 -u harness/bench_speed.py qwen3.8:27b nemotron command-r-plus llama4:scout 2>&1 | tee -a "$LOG"

say "ROUND2 DONE"
