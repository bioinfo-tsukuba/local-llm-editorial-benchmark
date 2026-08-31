#!/usr/bin/env bash
# Round 2, resumed. Two ollama instances are in play:
#   :11434  v0.17.6, system service -- the 4 models already pulled, and the
#           instance the first 127 cells were measured against
#   :11435  v0.32.15, user-space install -- qwen3.8:27b and gemma4, which
#           0.17.6 refuses with a 412
# They share one GPU, so nothing runs concurrently.
set -u
cd /home/dgx1/projects/2026/test-local-llm
LOG=logs/sweep.log
say(){ echo "=== [$(date -Is)] $*" | tee -a "$LOG"; }

OLD4="qwen3.6:27b,nemotron,command-r-plus,llama4:scout"
NEW2="qwen3.8:27b,gemma4"

say "round-2a: four models on the 0.17.6 instance"
python3 -u harness/run_t1.py    --models "$OLD4" --manuscripts MS-A,MS-B --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_t1.py    --models "$OLD4" --manuscripts MS-A,MS-B --seeds 42 --variant b 2>&1 | tee -a "$LOG"
python3 -u harness/run_tasks.py --tasks t3refs,t3ja,t4abs,t4ph,t6c,t6d,t7 --models "$OLD4" --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_tasks.py --tasks t2 --models "$OLD4" --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_t8.py    --models "$OLD4" --seeds 42 2>&1 | tee -a "$LOG"

say "waiting for the new-instance pulls"
while ! grep -q "NEW INSTANCE PULL DONE" logs/pull_new_instance.log 2>/dev/null; do sleep 30; done
grep "END " logs/pull_new_instance.log | tee -a "$LOG"

say "round-2b: qwen3.8 and gemma4 on the 0.32.15 instance"
export OLLAMA_PORT=11435
python3 -u harness/run_t1.py    --models "$NEW2" --manuscripts MS-A,MS-B --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_t1.py    --models "$NEW2" --manuscripts MS-A,MS-B --seeds 42 --variant b 2>&1 | tee -a "$LOG"
python3 -u harness/run_tasks.py --tasks t3refs,t3ja,t4abs,t4ph,t6c,t6d,t7 --models "$NEW2" --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_tasks.py --tasks t2 --models "$NEW2" --seeds 42 2>&1 | tee -a "$LOG"
python3 -u harness/run_t8.py    --models "$NEW2" --seeds 42 2>&1 | tee -a "$LOG"
.venv/bin/python -u harness/run_t5.py --models "$NEW2" --seeds 42 2>&1 | tee -a "$LOG"
unset OLLAMA_PORT

say "engine-version control: re-measure two cells of an unchanged model on 0.32.15"
# qwen3.6:27b exists on both instances only if pulled there; instead re-run the
# same model on the new engine to size the engine's effect on the numbers.
export OLLAMA_PORT=11435
/home/dgx1/.local/ollama-new/bin/ollama pull gpt-oss:20b >/dev/null 2>&1
OLLAMA_HOST=127.0.0.1:11435 OLLAMA_MODELS=/home/dgx1/.local/ollama-new-models \
  /home/dgx1/.local/ollama-new/bin/ollama list | tee -a "$LOG"
python3 -u harness/run_t1.py --models gpt-oss:20b --manuscripts MS-A --seeds 42 --overwrite 2>&1 | tee -a "$LOG"
unset OLLAMA_PORT

say "round-2 memory and speed (0.17.6 instance)"
python3 -u harness/measure_kv.py qwen3.6:27b nemotron command-r-plus llama4:scout 2>&1 | tee -a "$LOG"
python3 -u harness/bench_speed.py nemotron command-r-plus llama4:scout 2>&1 | tee -a "$LOG"

say "ROUND2 DONE"
