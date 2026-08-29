#!/usr/bin/env python3
"""Distinguish 'needs a bigger budget' from 'loops' for cells that returned nothing.

A model that hits the token cap having produced no answer is either still working or
stuck. The difference matters: raising the cap fixes the first and wastes GPU time on the
second. This re-runs the cell with the reasoning text captured and measures repetition.
"""
import json, pathlib, sys, re
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
from prompts import build_t1

ROOT = pathlib.Path(__file__).resolve().parent.parent
model = sys.argv[1] if len(sys.argv) > 1 else 'qwen3.5:35b-a3b-bf16'
ms = sys.argv[2] if len(sys.argv) > 2 else 'MS-B'
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 32768

g = (ROOT / 'data/guidelines/bppb_instructions_clean.txt').read_text()
m = (ROOT / f'data/manuscripts/{ms}.md').read_text()
txt, think, meta = oc.chat(model, build_t1(g, m), num_ctx=131072, seed=42,
                           num_predict=cap, timeout=7200)
sents = [s.strip() for s in re.split(r'[.\n]+', think) if len(s.strip()) > 40]
dup = Counter(sents)
rep = sum(c - 1 for c in dup.values() if c > 1)
out = {'model': model, 'manuscript': ms, 'num_predict': cap, 'meta': meta,
       'content_chars': len(txt), 'thinking_chars': len(think),
       'thinking_sentences': len(sents), 'repeated_sentences': rep,
       'repetition_rate': round(rep / max(1, len(sents)), 3),
       'most_repeated': dup.most_common(3),
       'thinking_tail': think[-1500:], 'content_head': txt[:800]}
(ROOT / f'results/loop_diag_{model.replace("/","_").replace(":","_")}_{ms}.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1))
print(f"done={meta['done_reason']} out={meta['output_tokens']} content={len(txt)} "
      f"thinking={len(think)} repetition={out['repetition_rate']}")
print('most repeated:', out['most_repeated'][:1])
