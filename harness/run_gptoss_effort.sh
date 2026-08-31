#!/usr/bin/env bash
# gpt-oss scored 0.22-0.25 on T1, but only because --think auto forces 'low' on it: at
# its own default it spent the entire budget reasoning and returned nothing. Now that
# num_ctx is 65536 and the cap is 24576, re-measure it at medium and high so the low
# score is not an artefact of the handicap we imposed.
set -u
cd "$(dirname "$0")/.."
while ! grep -q "CATCHUP DONE" logs/sweep.log 2>/dev/null; do sleep 60; done
for eff in medium high; do
  echo "=== [$(date -Is)] gpt-oss at reasoning effort: $eff" | tee -a logs/sweep.log
  python3 -u harness/run_t1.py --models gpt-oss:20b,gpt-oss:120b \
    --manuscripts MS-A,MS-B --seeds 42 --think $eff 2>&1 | tee -a logs/sweep.log
done
echo "=== [$(date -Is)] GPTOSS EFFORT DONE" | tee -a logs/sweep.log
