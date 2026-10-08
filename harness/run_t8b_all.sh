#!/bin/bash
# R2-3: T8 variant B across the 15 tool-capable models. Two of them live in the
# newer ollama store on port 11435, as in finalize.sh.
set -u
cd /home/dgx1/projects/2026/test-local-llm
LOG=logs/t8b_$(date +%Y%m%d_%H%M).log
mkdir -p logs results/t8b
P=.venv/bin/python
DEFAULT="command-r-plus,gpt-oss:120b,gpt-oss:20b,llama4:scout,magistral,mistral-small,nemotron,qwen3.5:122b-a10b-q4_K_M,qwen3.5:35b-a3b-bf16,qwen3.6:27b,qwen3.6:35b-a3b-bf16,qwen3.6:35b-a3b-q4_K_M,qwen3.6:35b-a3b-q8_0"
NEWPORT="qwen3.8:27b,gemma4"
echo "=== start $(date -Is)" | tee -a "$LOG"
$P -u harness/run_t8b.py --models "$DEFAULT" --seeds 42 2>&1 | tee -a "$LOG"
OLLAMA_PORT=11435 $P -u harness/run_t8b.py --models "$NEWPORT" --seeds 42 2>&1 | tee -a "$LOG"
echo "=== grade $(date -Is)" | tee -a "$LOG"
$P harness/grade_t8.py t8b 2>&1 | tee -a "$LOG"
echo "=== RUN COMPLETE $(date -Is) files=$(ls results/t8b/*.json 2>/dev/null | wc -l)" | tee -a "$LOG"
