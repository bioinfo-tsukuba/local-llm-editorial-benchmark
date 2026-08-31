#!/usr/bin/env python3
"""Runner for T2 (review generation), T3 (routine editorial work) and T4 (hallucination
resistance). One JSON record per (task, model, seed) in results/<task>/.

Usage: run_tasks.py --tasks t2,t3refs,t3ja,t4abs,t4ph [--models ...] [--seeds 42]
"""
import argparse, json, os, pathlib, re, sys, threading, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc


def _ollama_env():
    """`ollama list` must query the same instance the client talks to."""
    e = dict(os.environ)
    port = e.get('OLLAMA_PORT', '11434')
    e['OLLAMA_HOST'] = f'127.0.0.1:{port}'
    if port == '11435':
        e['OLLAMA_MODELS'] = '/home/dgx1/.local/ollama-new-models'
    return e


def _ollama_cmd():
    port = os.environ.get('OLLAMA_PORT', '11434')
    binary = ('/home/dgx1/.local/ollama-new/bin/ollama' if port == '11435' else 'ollama')
    return [binary, 'list']
import prompts
from run_t1 import slug, mem_sampler, extract_json, DEFAULT_MODELS, think_for, available_models, is_available

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _max_context(model):
    """Model's maximum context from `ollama show`, or None if unknown."""
    import subprocess, re as _re
    try:
        out = subprocess.run(_ollama_cmd()[:-1] + ['show', model],
                             capture_output=True, text=True, env=_ollama_env()).stdout
        m = _re.search(r'context length\s+(\d+)', out)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def load(p):
    return (ROOT / p).read_text()


def items_block(items, keys):
    out = []
    for it in items:
        out.append('\n'.join(f'{k}: {it[k]}' for k in keys if k in it))
    return '\n\n'.join(out)


def build(task, num_ctx_hint=None):
    """Return (messages, result_key, num_ctx)."""
    g = load('data/guidelines/bppb_instructions_clean.txt')
    if task == 't2':
        ms = load('data/preprints/arxiv_2512.17597.txt')
        # The preprint tokenises at 2.5 chars/token (LaTeX-derived text, many short
        # tokens), not the ~4 assumed from character count: the prompt is 65k tokens, not
        # the estimated 41k. At num_ctx=65536 it exactly filled the window, leaving no
        # room for output, and ollama shifted the context -- evicting the beginning of
        # the paper while the model was writing about it. Measure the real token count,
        # never estimate it from characters.
        return prompts.build_t2(ms), 'weaknesses', 131072
    if task == 't3refs':
        d = json.loads(load('data/t3/refs_input.json'))
        return prompts.build_t3refs(g, items_block(d['items'], ['id', 'input'])), 'conversions', 32768
    if task == 't3ja':
        d = json.loads(load('data/t3/ja_questions.json'))
        return prompts.build_t3ja(g, items_block(d['items'], ['id', 'q'])), 'answers', 32768
    if task == 't4abs':
        d = json.loads(load('data/t4/absent_rules.json'))
        return prompts.build_t4abs(g, items_block(d['items'], ['id', 'q'])), 'answers', 32768
    if task == 't6c':
        return prompts.build_t6(load('data/manuscripts/MS-C.md')), 'problems', 65536
    if task == 't6d':
        return prompts.build_t6(load('data/manuscripts/MS-D.md')), 'problems', 65536
    if task == 't7':
        return prompts.build_t7(g, load('data/manuscripts/MS-E.md')), 'findings', 65536
    if task == 't4ph':
        ms = load('data/manuscripts/MS-A.md')
        d = json.loads(load('data/t4/phantom_elements.json'))
        return prompts.build_t4ph(ms, items_block(d['items'], ['id', 'q'])), 'answers', 32768
    raise SystemExit(f'unknown task {task}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', default='t2,t3refs,t3ja,t4abs,t4ph,t6c,t6d,t7')
    ap.add_argument('--models', default=','.join(DEFAULT_MODELS))
    ap.add_argument('--seeds', default='42')
    ap.add_argument('--num-predict', type=int, default=24576)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--think', default='auto')
    a = ap.parse_args()

    have = available_models()
    for model in [m for m in a.models.split(',') if m]:
        if not is_available(model, have):
            print(f'[skip] {model}: not pulled', flush=True); continue
        for task in a.tasks.split(','):
            msgs, key, num_ctx = build(task)
            # ollama truncates silently when the prompt exceeds the window, so a
            # model whose maximum context is below the task's prompt would produce
            # a plausible-looking but meaningless cell. Skip and record why.
            need = sum(len(m['content']) for m in msgs) // 3
            cap = _max_context(model)
            if cap and need > cap:
                print(f'[skip] {task} {model}: needs ~{need} tokens, '
                      f'model max context is {cap}', flush=True)
                out = ROOT / 'results' / task
                out.mkdir(parents=True, exist_ok=True)
                for seed in [int(x) for x in a.seeds.split(',')]:
                    f = out / f'{slug(model)}__seed{seed}.json'
                    # --overwrite was ignored on this path, so a capability-skip
                    # record kept the timestamp of the first run it was written in
                    # and looked stale to any check that compares against the run
                    # start. The record is deterministic, so rewriting it is free.
                    if a.overwrite or not f.exists():
                        f.write_text(json.dumps(
                            {'task': task, 'model': model, 'seed': seed,
                             'error': f'context too small: needs ~{need} tokens, '
                                      f'model maximum is {cap}',
                             'skipped_reason': 'model-context-too-small',
                             'model_max_context': cap, 'required_tokens': need,
                             'meta': {}, key: None, 'n_items': None},
                            ensure_ascii=False, indent=1))
                continue
            out = ROOT / 'results' / task
            out.mkdir(parents=True, exist_ok=True)
            for seed in [int(s) for s in a.seeds.split(',')]:
                f = out / f'{slug(model)}__seed{seed}.json'
                if f.exists() and not a.overwrite:
                    print(f'[have] {task} {f.name}', flush=True); continue
                pc = sum(len(m['content']) for m in msgs)
                if a.dry_run:
                    print(f'[dry ] {task:8s} {model:45s} prompt_chars={pc} num_ctx={num_ctx}', flush=True)
                    continue
                print(f'[run ] {task:8s} {f.name}', flush=True, end=' ')
                memout, stop = {}, threading.Event()
                th = threading.Thread(target=mem_sampler, args=(stop, memout, model), daemon=True)
                th.start()
                err = None
                try:
                    txt, think, meta = oc.chat(model, msgs, num_ctx=num_ctx, seed=seed,
                                               num_predict=a.num_predict, think=think_for(model, a.think))
                except Exception as e:
                    txt, think, meta, err = '', '', {'model': model}, f'{type(e).__name__}: {e}'
                stop.set(); th.join(timeout=10)
                parsed, perr = extract_json(txt)
                got = parsed.get(key) if isinstance(parsed, dict) else None
                rec = {'task': task, 'model': model, 'seed': seed, 'num_ctx': num_ctx,
                       'error': err, 'parse_error': perr, 'result_key': key,
                       'n_items': len(got) if isinstance(got, list) else None,
                       'meta': meta | memout, key: got,
                       'raw_response': txt, 'thinking_chars': len(think)}
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                print(f"-> n={rec['n_items']} {meta.get('wall_s')}s "
                      f"prefill={meta.get('prefill_tok_s')} decode={meta.get('decode_tok_s')} "
                      f"in={meta.get('prompt_tokens')} out={meta.get('output_tokens')} "
                      f"vram={memout.get('peak_size_vram_mib')}MiB {err or perr or ''}", flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
