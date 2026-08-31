#!/usr/bin/env bash
# glm-4.5-air:q4 is excluded: it degenerates into a repetition loop on T1 (304 and 344
# near-identical findings, both hitting the 24,576 token cap after ~2,300 s), so a second
# prompt variant would cost 77 minutes to reproduce a known failure.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "GPTOSS EFFORT DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] T1 variant B (external checklist)" | tee -a logs/sweep.log
python3 -u harness/run_t1.py --variant b --seeds 42 --manuscripts MS-A,MS-B \
  --models "gpt-oss:120b,qwen3.6:35b-a3b-q8_0,hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0,qwen3.5:122b-a10b-q4_K_M" \
  2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] VARIANT B DONE" | tee -a logs/sweep.log
