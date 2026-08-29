#!/usr/bin/env bash
# Two-node follow-up. The first run showed two nodes are FASTER than one
# (prefill 1.78x, decode 1.15x), which contradicts the published report's 37.7 tok/s.
# Two differences explain it: that report split a model too large for one node, and
# it ran over TCP/IP while this cluster negotiates RoCEv2/RDMA. These runs test where
# the speedup comes from and where it stops.
#
#  A. Does the gain hold for a model that comfortably fits one node?
#     If splitting a 17 GB model also gains ~1.8x, the win is parallel compute, not
#     relief from memory pressure -- and then two nodes help even at our scale.
#  B. Does it hold across context lengths, or only at long prompts?
#  C. What does RDMA contribute? Force TCP by pointing at the management LAN, where
#     there is no RoCE path, and compare.
set -u
cd /home/dgx1/projects/2026/test-local-llm
SRC=/home/dgx1/models/llama.cpp-src/build/bin
export LD_LIBRARY_PATH=$SRC:/usr/local/cuda/lib64
LOG=logs/twonode.log
OUT=results/twonode
mkdir -p "$OUT"
RPC_FAST=192.168.102.2:50052     # ConnectX-7, RoCE available
RPC_SLOW=172.21.3.157:50052      # management LAN, no RoCE path
say(){ echo "=== [$(date -Is)] $*" | tee -a "$LOG"; }

BIG=/home/dgx1/models/glm45air/GLM-4.5-Air-UD-Q4_K_XL-merged.gguf
SMALL=$(ls /home/dgx1/.local/ollama-new-models/blobs/sha256-* 2>/dev/null \
        | xargs -r ls -S 2>/dev/null | head -1)

say "A/B: small model (fits one node easily), one vs two"
if [ -n "${SMALL:-}" ] && [ -f "$SMALL" ]; then
  for pp in 4096 12288 32768; do
    say "SMALL ONE  pp=$pp"
    "$SRC/llama-bench" -m "$SMALL" -p $pp -n 128 -r 2 2>&1 | grep -E "^\|" | tail -2 | tee -a "$LOG"
    say "SMALL TWO  pp=$pp"
    "$SRC/llama-bench" -m "$SMALL" --rpc "$RPC_FAST" -p $pp -n 128 -r 2 2>&1 | grep -E "^\|" | tail -2 | tee -a "$LOG"
  done
else
  say "SKIP small-model arm: no standalone gguf on disk (ollama stores blobs unnamed)"
fi

say "B: big model across context lengths"
for pp in 4096 32768 131072; do
  say "BIG ONE  pp=$pp"
  "$SRC/llama-bench" -m "$BIG" -p $pp -n 128 -r 1 2>&1 | grep -E "^\|" | tail -2 | tee -a "$LOG"
  say "BIG TWO  pp=$pp"
  "$SRC/llama-bench" -m "$BIG" --rpc "$RPC_FAST" -p $pp -n 128 -r 1 2>&1 | grep -E "^\|" | tail -2 | tee -a "$LOG"
done

say "C: interconnect contribution -- same split over the management LAN (no RoCE)"
if timeout 5 bash -c "echo > /dev/tcp/172.21.3.157/50052" 2>/dev/null; then
  for pp in 12288 71230; do
    say "BIG TWO-TCP pp=$pp"
    "$SRC/llama-bench" -m "$BIG" --rpc "$RPC_SLOW" -p $pp -n 128 -r 1 2>&1 | grep -E "^\|" | tail -2 | tee -a "$LOG"
  done
else
  say "SKIP TCP arm: RPC server is not reachable on the management LAN"
fi

say "TWONODE MATRIX DONE"
