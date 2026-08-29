#!/usr/bin/env bash
# Bring up llama.cpp RPC across the two Sparks and check it works.
#
# Why llama.cpp RPC and not vLLM or NCCL: the published two-node report for this
# hardware found NVIDIA's native multi-node stack is not ready for GB10/SM121 --
# vLLM+Ray fails because Ray registers the GPU as accelerator_type:GB10 while vLLM
# expects the GPU key, and TensorRT-LLM lacks SM121 GEMM kernels. RPC over TCP was
# the only route that worked there, so it is the route worth measuring here.
set -u
PEER=192.168.102.2
LOCAL=192.168.102.1
BIN=/home/dgx1/models/llama-b10549
PORT=50052

echo "=== 1. peer reachable"
ping -c2 -W2 "$PEER" >/dev/null || { echo "FAIL: $PEER unreachable"; exit 1; }
ssh -o BatchMode=yes -o ConnectTimeout=6 "$PEER" true || {
  echo "FAIL: ssh to $PEER needs a key in its authorized_keys"; exit 1; }
echo "  ok"

echo "=== 2. ship the runtime to the peer"
ssh "$PEER" 'mkdir -p /tmp/llama-rpc'
rsync -a --info=progress2 "$BIN/ggml-rpc-server" "$BIN"/lib*.so* "$PEER":/tmp/llama-rpc/ 2>/dev/null \
  || scp -q "$BIN/ggml-rpc-server" "$BIN"/lib*.so* "$PEER":/tmp/llama-rpc/
ssh "$PEER" 'chmod +x /tmp/llama-rpc/ggml-rpc-server; ls /tmp/llama-rpc | wc -l'

echo "=== 3. start the RPC server on the peer"
ssh "$PEER" "pkill -f ggml-rpc-server; sleep 1; \
  LD_LIBRARY_PATH=/tmp/llama-rpc setsid nohup /tmp/llama-rpc/ggml-rpc-server \
  -H 0.0.0.0 -p $PORT > /tmp/rpc.log 2>&1 < /dev/null & sleep 3; tail -3 /tmp/rpc.log"

echo "=== 4. port open from here?"
timeout 5 bash -c "echo > /dev/tcp/$PEER/$PORT" && echo "  $PEER:$PORT OPEN" \
  || { echo "FAIL: RPC port not reachable"; exit 1; }

echo "=== 5. also start one locally, so a run can use both GPUs"
pkill -f ggml-rpc-server 2>/dev/null; sleep 1
LD_LIBRARY_PATH=$BIN setsid nohup "$BIN/ggml-rpc-server" -H 0.0.0.0 -p $PORT \
  > /tmp/rpc_local.log 2>&1 < /dev/null &
sleep 3; tail -3 /tmp/rpc_local.log
echo
echo "READY: --rpc $LOCAL:$PORT,$PEER:$PORT"
