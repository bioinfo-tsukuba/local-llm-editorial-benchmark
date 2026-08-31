#!/usr/bin/env bash
# MS-B was corrected mid-sweep (figures 3/4 cited out of order -- a real defect a model
# found on the supposedly compliant control), and two cells were truncated at the old
# token cap. This re-runs whatever T1 cells are missing.
#
# Waits for the GLM KV/speed supplement, not for SPEED BENCH DONE: both chains were
# originally armed on the same marker and started together, and memory measurements are
# invalid while another model is resident.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "GLM KV/SPEED DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
echo "=== [$(date -Is)] T1 catch-up for corrected MS-B" | tee -a logs/sweep.log
ALL="gpt-oss:20b,qwen3.6:35b-a3b-q4_K_M,qwen3.6:35b-a3b-q8_0,qwen3.6:35b-a3b-bf16,qwen3.5:35b-a3b-bf16,qwen3.5:122b-a10b-q4_K_M,gpt-oss:120b,hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0,glm-4.5-air:q4"
python3 -u harness/run_t1.py --models "$ALL" --manuscripts MS-A,MS-B --seeds 42 2>&1 | tee -a logs/sweep.log
python3 -u harness/run_t1.py --models qwen3.6:35b-a3b-q8_0,gpt-oss:120b --manuscripts MS-A,MS-B --seeds 43,44 2>&1 | tee -a logs/sweep.log
echo "=== [$(date -Is)] CATCHUP DONE" | tee -a logs/sweep.log
