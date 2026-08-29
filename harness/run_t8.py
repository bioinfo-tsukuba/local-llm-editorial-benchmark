#!/usr/bin/env python3
"""T8: reference verification with external lookup tools.

Runs a real tool-calling loop against ollama: the model may call lookup_doi and
search_reference, the results are executed for real against Crossref/NLM and fed
back, and the loop continues until the model answers or hits a call budget.

Everything is recorded -- every tool call the model made, with its arguments --
so the failure modes can be separated: never calling a tool, calling it with a
malformed argument, calling it and then ignoring the result, or answering from
the weights while claiming to have looked it up.
"""
import argparse, json, pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
import refttools
from run_t1 import slug, mem_sampler, extract_json, think_for

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_CALLS = 24

SYSTEM = """You are a journal editorial assistant verifying reference lists.

You have two tools that query authoritative bibliographic databases. Use them:
the journal's required abbreviations and the existence of a DOI are facts you
must look up, not recall.

Rules:
- Never state a DOI, journal abbreviation, volume or year that a tool did not
  return. If a lookup fails, say the reference could not be verified.
- A DOI that resolves is not automatically the right DOI. Compare the returned
  title and authors against the reference you were given.
- The journal requires Index Medicus / MEDLINE style abbreviated journal titles.
- Output valid JSON only, after you have finished calling tools."""

USER = """Verify each reference below. For each one, use the tools to check that
it exists, that the DOI is correct for that reference, and that the journal name
is in the required abbreviated form.

Output a single JSON object:

{{"checks": [
  {{"id": "<item id>",
   "verified": true|false,
   "journal_abbreviated": "<the abbreviated journal title, or null if unverified>",
   "problems": ["<each discrepancy you found, or an empty list>"],
   "corrected_doi": "<the correct DOI if the given one is wrong, else null>"}}
]}}

=== REFERENCES ===

{items}

Now verify them, then output the JSON object."""


def run_cell(model, items_text, seed, think, num_ctx=32768, num_predict=16384):
    msgs = [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': USER.format(items=items_text)}]
    trace, calls, t0 = [], 0, time.monotonic()
    meta = {}
    while True:
        txt, thinking, meta = oc.chat(model, msgs, num_ctx=num_ctx, seed=seed,
                                      num_predict=num_predict, think=think,
                                      tools=refttools.TOOL_SPECS, timeout=3600)
        tc = meta.pop('tool_calls', None) or []
        if not tc:
            return txt, thinking, meta, trace, calls, round(time.monotonic() - t0, 1)
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
            if fn in refttools.DISPATCH and calls <= MAX_CALLS:
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
        if calls >= MAX_CALLS:
            msgs.append({'role': 'user', 'content':
                         'Tool budget exhausted. Output the JSON object now using '
                         'what you have; mark anything unverified as unverified.'})


def _summarise(res):
    if not isinstance(res, dict):
        return str(res)[:120]
    if 'candidates' in res:
        return f"{len(res['candidates'])} candidates: " + \
               ', '.join(f"{c.get('doi')}" for c in res['candidates'][:3])
    if res.get('found'):
        return f"{res.get('journal_abbreviated')} {res.get('volume')} ({res.get('year')}) {res.get('doi')}"
    return res.get('note') or res.get('error') or 'not found'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True)
    ap.add_argument('--seeds', default='42')
    ap.add_argument('--think', default='auto')
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()

    d = json.loads((ROOT / 'data/t8/items.json').read_text())
    items_text = '\n\n'.join(f"id: {i['id']}\n{i['input']}" for i in d['items'])
    out = ROOT / 'results' / 't8'
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
            err = None
            try:
                txt, thinking, meta, trace, calls, wall = run_cell(
                    model, items_text, seed, think_for(model, a.think))
            except Exception as e:
                txt, thinking, meta, trace, calls, wall = '', '', {'model': model}, [], 0, 0
                err = f'{type(e).__name__}: {e}'
            stop.set(); th.join(timeout=10)
            parsed, perr = extract_json(txt)
            checks = parsed.get('checks') if isinstance(parsed, dict) else None
            rec = {'task': 'T8', 'model': model, 'seed': seed, 'error': err,
                   'parse_error': perr, 'n_tool_calls': calls,
                   'n_checks': len(checks) if isinstance(checks, list) else None,
                   'meta': meta | memout, 'checks': checks, 'tool_trace': trace,
                   'raw_response': txt, 'thinking_chars': len(thinking), 'wall_s': wall}
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            print(f"-> calls={calls} checks={rec['n_checks']} {wall}s {err or perr or ''}",
                  flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
