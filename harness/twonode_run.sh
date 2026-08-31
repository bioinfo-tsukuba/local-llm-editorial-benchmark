#!/usr/bin/env bash
# Two-node measurement, end to end. Waits for the CUDA build, ships it to the peer,
# starts an RPC server on each node, then benchmarks the same model on one node and
# on two so the cost of splitting is isolated from any change of model.
#
# The published two-node report used Qwen3-235B, which does not fit on one node, so
# its numbers mix the distribution overhead with a much larger model. This measures
# both configurations on a model that fits either way.
set -u
cd /home/dgx1/projects/2026/test-local-llm
LOG=logs/twonode.log
SRC=/home/dgx1/models/llama.cpp-src/build/bin
PEER=192.168.102.2
PORT=50052
OUT=results/twonode
mkdir -p "$OUT"
say(){ echo "=== [$(date -Is)] $*" | tee -a "$LOG"; }

say "waiting for the CUDA build"
while ! grep -q "build rc=" /tmp/build_wrap.log 2>/dev/null; do sleep 30; done
grep "build rc=" /tmp/build_wrap.log | tee -a "$LOG"
[ -x "$SRC/ggml-rpc-server" ] || { say "FAIL: no ggml-rpc-server"; exit 1; }
LD_LIBRARY_PATH=$SRC "$SRC/ggml-rpc-server" --help 2>&1 | grep load_backend | tee -a "$LOG"

say "shipping to the peer"
ssh -o BatchMode=yes "$PEER" 'rm -rf /tmp/llama-cuda && mkdir -p /tmp/llama-cuda'
scp -q "$SRC"/ggml-rpc-server "$SRC"/llama-bench "$SRC"/*.so* "$PEER":/tmp/llama-cuda/ 2>/dev/null
ssh -o BatchMode=yes "$PEER" 'chmod +x /tmp/llama-cuda/ggml-rpc-server /tmp/llama-cuda/llama-bench 2>/dev/null; ls /tmp/llama-cuda | wc -l' | tee -a "$LOG"

say "starting RPC servers"
ssh -o BatchMode=yes "$PEER" "pkill -f ggml-rpc-server; sleep 1; \
  cd /tmp/llama-cuda && LD_LIBRARY_PATH=/tmp/llama-cuda:/usr/local/cuda-13.0/lib64 \
  nohup ./ggml-rpc-server -H 0.0.0.0 -p $PORT > /tmp/rpc.log 2>&1 &" 
sleep 6
ssh -o BatchMode=yes "$PEER" "head -6 /tmp/rpc.log" | tee -a "$LOG"
timeout 5 bash -c "echo > /dev/tcp/$PEER/$PORT" \
  && say "peer RPC port open" || { say "FAIL: peer RPC port closed"; exit 1; }

say "benchmarking"
export LD_LIBRARY_PATH=$SRC:/usr/local/cuda/lib64
M=/home/dgx1/models/glm45air/GLM-4.5-Air-UD-Q4_K_XL-merged.gguf
for pp in 12288 71230; do
  say "two nodes, prompt $pp"
  "$SRC/llama-bench" -m "$M" --rpc "$PEER:$PORT" -p $pp -n 128 -r 1 2>&1 | tee -a "$LOG" | tail -4
  say "one node, prompt $pp"
  "$SRC/llama-bench" -m "$M" -p $pp -n 128 -r 1 2>&1 | tee -a "$LOG" | tail -4
done
say "TWONODE DONE"
