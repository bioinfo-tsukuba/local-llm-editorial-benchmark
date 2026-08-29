#!/usr/bin/env bash
# Full sweep. Waits for model downloads to finish first so that timing numbers are not
# contaminated by concurrent NVMe/network load, then runs every task sequentially.
#
# Seed policy: the whole matrix runs at seed 42; two representative models
# (qwen3.6 q8 and gpt-oss:120b) additionally run seeds 43 and 44 so run-to-run
# variance can be quantified without paying for it on every cell.
set -u
cd "$(dirname "$0")/.."
LOG=logs/sweep.log
say(){ echo "=== [$(date -Is)] $*" | tee -a "$LOG"; }

say "waiting for model downloads"
while ! grep -q "ALL DONE" logs/pull_models.log 2>/dev/null; do sleep 30; done
say "downloads complete"
ollama list | tee -a "$LOG"

ALL="gpt-oss:20b,qwen3.6:35b-a3b-q4_K_M,qwen3.6:35b-a3b-q8_0,qwen3.6:35b-a3b-bf16,qwen3.5:35b-a3b-bf16,qwen3.5:122b-a10b-q4_K_M,gpt-oss:120b,hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0,hf.co/unsloth/GLM-4.5-Air-GGUF:UD-Q4_K_XL"
VAR="qwen3.6:35b-a3b-q8_0,gpt-oss:120b"

say "T1 full matrix, seed 42"
python3 -u harness/run_t1.py --models "$ALL" --manuscripts MS-A,MS-B --seeds 42 2>&1 | tee -a "$LOG"

say "T1 variance subset, seeds 43,44"
python3 -u harness/run_t1.py --models "$VAR" --manuscripts MS-A,MS-B --seeds 43,44 2>&1 | tee -a "$LOG"

say "T3/T4 full matrix, seed 42"
python3 -u harness/run_tasks.py --tasks t3refs,t3ja,t4abs,t4ph --models "$ALL" --seeds 42 2>&1 | tee -a "$LOG"

say "T2 (41k-token context) full matrix, seed 42"
python3 -u harness/run_tasks.py --tasks t2 --models "$ALL" --seeds 42 2>&1 | tee -a "$LOG"

say "T5 vision models"
.venv/bin/python -u harness/run_t5.py --seeds 42 2>&1 | tee -a "$LOG"

say "ALL TASKS DONE"
