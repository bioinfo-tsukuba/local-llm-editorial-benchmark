#!/usr/bin/env python3
"""T8 variant B: one reference per call, against T8's single call for all eight.

Reviewer 2 asked what prompt structure does on tasks other than T1, and named T8
because Figure 5 shows its rank ordering is unlike T1's. T1's variant C splits the
guidelines into eight areas and gives each its own call; T8 has no guideline document
to split, but it has eight references, so the structurally equivalent manipulation is
to give each reference its own call. That is what this runs.

Everything else is held fixed: the same system prompt, the same tools, the same model
set, seed 42, the same context and generation budgets. Only the decomposition changes.

Results go to results/t8b/, never results/t8/, so the reported T8 numbers cannot move.
Each record is shaped exactly like a run_t8.py record -- the eight single-item answers
are concatenated into one `checks` list and the tool traces appended -- so grade_t8.py
scores it with no change beyond being pointed at the other directory.

Usage: python3 harness/run_t8b.py --models a,b,c [--seeds 42] [--overwrite]
"""
import argparse, json, pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
import refttools
from run_t1 import slug, mem_sampler, extract_json, think_for
from run_t8 import SYSTEM, MAX_CALLS, _summarise

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Per-reference budget. run_t8.py allows 24 calls for all eight references; eight
# separate calls get three each, so the total budget is unchanged and the comparison
# is not confounded by one arm being allowed more lookups.
CALLS_PER_ITEM = 3

USER_ONE = """Verify the single reference below. Use the tools to check that it
exists, that the DOI is correct for that reference, and that the journal name is in
the required abbreviated form.

Check this reference only. The other references in the list are being checked
separately.

Output a single JSON object:

{{"checks": [
  {{"id": "<item id>",
   "verified": true|false,
   "journal_abbreviated": "<the abbreviated journal title, or null if unverified>",
   "problems": ["<each discrepancy you found, or an empty list>"],
   "corrected_doi": "<the correct DOI if the given one is wrong, else null>"}}
]}}

=== REFERENCE ===

{item}

Now verify it, then output the JSON object."""


def run_one(model, item_text, seed, think, num_ctx, num_predict):
    """One reference, one conversation. Returns (checks, trace, calls, meta, raw)."""
    msgs = [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': USER_ONE.format(item=item_text)}]
    trace, calls, meta = [], 0, {}
    while True:
        txt, thinking, meta = oc.chat(model, msgs, num_ctx=num_ctx, seed=seed,
                                      num_predict=num_predict, think=think,
                                      tools=refttools.TOOL_SPECS, timeout=3600)
        tc = meta.pop('tool_calls', None) or []
        if not tc:
            parsed, perr = extract_json(txt)
            checks = parsed.get('checks') if isinstance(parsed, dict) else None
            return (checks if isinstance(checks, list) else []), trace, calls, meta, txt, perr
        msgs.append({'role': 'assistant', 'content': txt or '', 'tool_calls': tc})
        for c in tc:
            fn = (c.get('function') or {}).get('name')
            args = (c.get('function') or {}).get('arguments') or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {'_raw': args}
            calls += 1
            if fn in refttools.DISPATCH and calls <= CALLS_PER_ITEM:
                try:
                    res = refttools.DISPATCH[fn](*[args.get(k) for k in
                                                   (['doi'] if fn == 'lookup_doi'
                                                    else ['bibliographic'])])
                    err = None
                except Exception as e:
                    res, err = {'error': str(e)[:200]}, str(e)[:200]
            else:
                res = {'error': f'unknown tool {fn}' if fn not in refttools.DISPATCH
                       else 'tool-call budget exhausted'}
                err = res['error']
            trace.append({'n': calls, 'tool': fn, 'args': args,
                          'result_summary': _summarise(res), 'error': err})
            msgs.append({'role': 'tool', 'content': json.dumps(res, ensure_ascii=False)})
        if calls >= CALLS_PER_ITEM:
            msgs.append({'role': 'user', 'content':
                         'Tool budget exhausted. Output the JSON object now using '
                         'what you have; mark anything unverified as unverified.'})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True)
    ap.add_argument('--seeds', default='42')
    ap.add_argument('--think', default='auto')
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()

    items = json.loads((ROOT / 'data/t8/items.json').read_text())['items']
    out = ROOT / 'results' / 't8b'
    out.mkdir(parents=True, exist_ok=True)

    for model in a.models.split(','):
        for seed in [int(s) for s in a.seeds.split(',')]:
            f = out / f'{slug(model)}__seed{seed}.json'
            if f.exists() and not a.overwrite:
                print(f'[have] {f.name}', flush=True); continue
            print(f'[run ] {f.name}', flush=True, end=' ')
            memout, stop = {}, threading.Event()
            th = threading.Thread(target=mem_sampler, args=(stop, memout, model), daemon=True)
            th.start()
            t0 = time.monotonic()
            all_checks, all_trace, total_calls, perrs, raws = [], [], 0, [], []
            meta, err = {}, None
            think = think_for(model, a.think)
            for it in items:
                try:
                    ch, tr, n, meta, raw, perr = run_one(
                        model, f"id: {it['id']}\n{it['input']}", seed, think,
                        32768, 16384)
                except Exception as e:
                    ch, tr, n, raw, perr = [], [], 0, '', f'{type(e).__name__}: {e}'
                    err = err or perr
                # a single-item answer may omit the id; supply it so the grader,
                # which keys on id, is not scoring a blank
                for c in ch:
                    if isinstance(c, dict) and not c.get('id'):
                        c['id'] = it['id']
                all_checks += [c for c in ch if isinstance(c, dict)]
                all_trace += [dict(t, item=it['id']) for t in tr]
                total_calls += n
                if perr:
                    perrs.append(f"{it['id']}: {perr}")
                raws.append(f"=== {it['id']} ===\n{raw}")
            stop.set(); th.join(timeout=10)
            wall = round(time.monotonic() - t0, 1)
            rec = {'task': 'T8', 'variant': 'b', 'model': model, 'seed': seed,
                   'error': err, 'parse_error': '; '.join(perrs),
                   'n_tool_calls': total_calls,
                   'n_checks': len(all_checks),
                   'n_calls_made': len(items),
                   'meta': meta | memout, 'checks': all_checks,
                   'tool_trace': all_trace,
                   'raw_response': '\n\n'.join(raws), 'thinking_chars': 0,
                   'wall_s': wall}
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            print(f'-> calls={total_calls} checks={len(all_checks)} {wall}s '
                  f"{err or '; '.join(perrs) or ''}", flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
