#!/usr/bin/env bash
# Two-node inference measurement, mirroring the single-node numbers so they can be
# compared directly: prefill and decode at the input lengths the editorial tasks
# actually use (a manuscript is ~12k tokens, a full paper ~70k).
set -u
PEER=192.168.102.2:50052
LOCAL=192.168.102.1:50052
BIN=/home/dgx1/models/llama-b10549
OUT=/home/dgx1/projects/2026/test-local-llm/results/twonode
mkdir -p "$OUT"
export LD_LIBRARY_PATH=$BIN

# A model that already fits on one node, so the comparison isolates the cost of
# splitting rather than confounding it with a change of model.
M=${1:-/home/dgx1/models/glm45air/GLM-4.5-Air-UD-Q4_K_XL-merged.gguf}
NAME=$(basename "$M" .gguf)

for np in 128 512; do
  for pp in 12288 71230; do
    echo "=== [$(date -Is)] two-node pp=$pp tg=$np"
    "$BIN/llama-bench" -m "$M" --rpc "$LOCAL,$PEER" -p $pp -n $np -r 1 \
      -o json 2>/dev/null > "$OUT/two_${NAME}_pp${pp}_tg${np}.json" || echo "  failed"
    echo "=== [$(date -Is)] single-node pp=$pp tg=$np"
    "$BIN/llama-bench" -m "$M" -p $pp -n $np -r 1 \
      -o json 2>/dev/null > "$OUT/one_${NAME}_pp${pp}_tg${np}.json" || echo "  failed"
  done
done
echo "done -> $OUT"
