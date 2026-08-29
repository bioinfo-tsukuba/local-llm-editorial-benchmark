#!/usr/bin/env bash
# T2 is re-run from scratch at num_ctx=131072: the first attempt was invalid because the
# 65k-token prompt exactly filled a 65536-token window.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "T6/T7 DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
ALL="gpt-oss:20b,qwen3.6:35b-a3b-q4_K_M,qwen3.6:35b-a3b-q8_0,qwen3.6:35b-a3b-bf16,qwen3.5:35b-a3b-bf16,qwen3.5:122b-a10b-q4_K_M,gpt-oss:120b,hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0,glm-4.5-air:q4"
echo "=== [$(date -Is)] T2 rerun at num_ctx=131072" | tee -a logs/sweep.log
python3 -u harness/run_tasks.py --tasks t2 --models "$ALL" --seeds 42 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] T2 RERUN DONE" | tee -a logs/sweep.log
