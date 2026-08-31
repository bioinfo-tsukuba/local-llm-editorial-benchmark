#!/usr/bin/env python3
"""Re-parse stored raw responses for cells whose JSON failed to parse.

A malformed-JSON cell is not a failed measurement: the model's answer is in
raw_response, so the cell can be recovered without spending GPU time again.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from run_t1 import extract_json

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEYS = {'t1': 'findings', 't2': 'weaknesses', 't3refs': 'conversions',
        't3ja': 'answers', 't4abs': 'answers', 't4ph': 'answers', 't5': 'defects'}
n = 0
for d in sorted((ROOT / 'results').iterdir()):
    if not d.is_dir() or d.name.startswith('_'):
        continue
    key = KEYS.get(d.name)
    for f in sorted(d.glob('*.json')):
        r = json.loads(f.read_text())
        # Also reprocess cells that "parsed" but yielded nothing: a model can emit valid
        # JSON under a different key, or wrap it in <think> tags, in which case
        # parse_error is None while the payload is empty. Skipping those silently lost
        # four glm-4.5-air cells that had in fact answered.
        k0 = r.get('result_key') or KEYS.get(d.name)
        empty = r.get(k0) in (None, []) and r.get('n_items') in (None, 0) \
            and r.get('n_findings') in (None, 0) and r.get('n_defects') in (None, 0)
        if not r.get('raw_response'):
            continue
        if not r.get('parse_error') and not empty:
            continue
        parsed, perr = extract_json(r['raw_response'])
        if parsed is None:
            print(f'still broken: {d.name}/{f.name} ({perr})'); continue
        k = r.get('result_key') or key
        got = parsed.get(k) if isinstance(parsed, dict) else None
        if got is None and isinstance(parsed, dict) and '__salvaged__' in parsed:
            got = parsed['__salvaged__']
            r['schema_break'] = True
        r['parse_error'] = perr
        if d.name == 't1':
            r['findings'] = got; r['n_findings'] = len(got) if isinstance(got, list) else None
        elif d.name == 't5':
            r['defects'] = got; r['n_defects'] = len(got) if isinstance(got, list) else None
        else:
            r[k] = got; r['n_items'] = len(got) if isinstance(got, list) else None
        f.write_text(json.dumps(r, ensure_ascii=False, indent=1))
        print(f'recovered: {d.name}/{f.name} -> {len(got) if isinstance(got,list) else None} items ({perr})')
        n += 1
print(f'\n{n} cell(s) recovered')
