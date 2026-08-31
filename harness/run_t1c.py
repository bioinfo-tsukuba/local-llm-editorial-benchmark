#!/usr/bin/env python3
"""T1 variant C: one call per checklist area, findings merged.

variant B put eight areas in one prompt and doubled HARD-side detection. This asks
whether splitting them into eight calls helps further. Records each area separately
so the cost of the extra prefills is visible against what they buy.
"""
import argparse, json, os, pathlib, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
import prompts
from run_t1 import slug, mem_sampler, extract_json, think_for, available_models, is_available

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'results' / 't1c'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True)
    ap.add_argument('--manuscripts', default='MS-A,MS-B')
    ap.add_argument('--seeds', default='42')
    ap.add_argument('--num-ctx', type=int, default=65536)
    ap.add_argument('--num-predict', type=int, default=8192)
    ap.add_argument('--think', default='auto')
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    g = (ROOT / 'data/guidelines/bppb_instructions_clean.txt').read_text()
    have = available_models()

    for model in a.models.split(','):
        if not is_available(model, have):
            print(f'[skip] {model}: not pulled', flush=True); continue
        for ms in a.manuscripts.split(','):
            man = (ROOT / f'data/manuscripts/{ms}.md').read_text()
            for seed in [int(s) for s in a.seeds.split(',')]:
                f = OUT / f'{slug(model)}__{ms}__seed{seed}.json'
                if f.exists() and not a.overwrite:
                    print(f'[have] {f.name}', flush=True); continue
                print(f'[run ] {f.name}', flush=True, end=' ')
                memout, stop = {}, threading.Event()
                th = threading.Thread(target=mem_sampler, args=(stop, memout, model), daemon=True)
                th.start()
                areas, all_f, t0 = [], [], time.monotonic()
                for en, ja in prompts.T1C_AREAS:
                    try:
                        txt, _, meta = oc.chat(
                            model, prompts.build_t1c(g, man, en, ja),
                            num_ctx=a.num_ctx, seed=seed, num_predict=a.num_predict,
                            think=think_for(model, a.think), timeout=3600)
                        parsed, perr = extract_json(txt)
                        got = parsed.get('findings') if isinstance(parsed, dict) else None
                        got = got or []
                    except Exception as e:
                        got, perr, meta = [], f'{type(e).__name__}: {e}', {}
                    for x in got:
                        if isinstance(x, dict):
                            x['_area'] = en
                    all_f += [x for x in got if isinstance(x, dict)]
                    areas.append({'area': en, 'n': len(got), 'parse_error': perr,
                                  'wall_s': meta.get('wall_s'),
                                  'prompt_tokens': meta.get('prompt_tokens'),
                                  'output_tokens': meta.get('output_tokens'),
                                  'prefill_tok_s': meta.get('prefill_tok_s')})
                stop.set(); th.join(timeout=10)
                rec = {'task': 'T1', 'variant': 'c', 'model': model, 'manuscript': ms,
                       'seed': seed, 'num_ctx': a.num_ctx, 'num_predict': a.num_predict,
                       'error': None, 'parse_error': None,
                       'n_findings': len(all_f), 'findings': all_f,
                       'per_area': areas,
                       'meta': {'wall_s': round(time.monotonic() - t0, 1),
                                'output_tokens': sum(x['output_tokens'] or 0 for x in areas),
                                'prompt_tokens': sum(x['prompt_tokens'] or 0 for x in areas),
                                **memout},
                       'raw_response': '', 'thinking_chars': 0}
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                print(f"-> n={len(all_f)} {rec['meta']['wall_s']}s "
                      f"out={rec['meta']['output_tokens']}", flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
