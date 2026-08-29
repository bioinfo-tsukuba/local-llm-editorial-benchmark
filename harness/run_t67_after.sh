#!/usr/bin/env bash
# T6 (scientific self-consistency) and T7 (category-conditional rules) were added after
# T1/T3/T4 turned out to be saturated on their easy halves. These are the tasks meant to
# discriminate: T6 needs arithmetic and cross-section comparison, T7 needs conditional
# reasoning about which rules apply to the declared category.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "GLM TASKS DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
ALL="gpt-oss:20b,qwen3.6:35b-a3b-q4_K_M,qwen3.6:35b-a3b-q8_0,qwen3.6:35b-a3b-bf16,qwen3.5:35b-a3b-bf16,qwen3.5:122b-a10b-q4_K_M,gpt-oss:120b,hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0,glm-4.5-air:q4"
echo "=== [$(date -Is)] T6/T7 full matrix" | tee -a logs/sweep.log
python3 -u harness/run_tasks.py --tasks t6c,t6d,t7 --models "$ALL" --seeds 42 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] T6/T7 DONE" | tee -a logs/sweep.log
