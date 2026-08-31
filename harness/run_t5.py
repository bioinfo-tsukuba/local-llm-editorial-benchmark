#!/usr/bin/env python3
"""T5: figure/table checking with vision models. One record per (model, figure, seed)."""
import argparse, base64, json, pathlib, sys, threading, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
import prompts


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
    return [binary, 'list'], prompts
from run_t1 import slug, mem_sampler, extract_json, think_for, available_models, is_available

ROOT = pathlib.Path(__file__).resolve().parent.parent
VLM_MODELS = ['qwen3-vl:30b-a3b-instruct', 'qwen3-vl:30b-a3b-instruct-bf16',
              'qwen3.6:35b-a3b-q8_0', 'gemma3:4b']


def props(path):
    from PIL import Image
    im = Image.open(path)
    dpi = im.info.get('dpi')
    return (f'{path.name}, {im.format}, {im.size[0]}x{im.size[1]} px, '
            f'dpi={round(dpi[0]) if dpi else "unknown"}, '
            f'{path.stat().st_size // 1024} KB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', default=','.join(VLM_MODELS))
    ap.add_argument('--seeds', default='42')
    ap.add_argument('--num-predict', type=int, default=8192)
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--think', default='auto')
    a = ap.parse_args()

    gt = json.loads((ROOT / 'data/groundtruth/T5_groundtruth.json').read_text())
    out = ROOT / 'results' / 't5'; out.mkdir(parents=True, exist_ok=True)
    have = available_models()
    for model in a.models.split(','):
        if model not in have:
            print(f'[skip] {model}: not pulled', flush=True); continue
        for item in gt['items']:
            img = ROOT / item['image']
            b64 = base64.b64encode(img.read_bytes()).decode()
            msgs = prompts.build_t5(item['legend'], props(img))
            msgs[-1]['images'] = [b64]
            for seed in [int(s) for s in a.seeds.split(',')]:
                f = out / f"{slug(model)}__{item['id']}__seed{seed}.json"
                if f.exists() and not a.overwrite:
                    print(f'[have] {f.name}', flush=True); continue
                print(f'[run ] {f.name}', flush=True, end=' ')
                memout, stop = {}, threading.Event()
                th = threading.Thread(target=mem_sampler, args=(stop, memout, model), daemon=True); th.start()
                err = None
                try:
                    txt, think, meta = oc.chat(model, msgs, num_ctx=16384, seed=seed,
                                               num_predict=a.num_predict, think=think_for(model, a.think))
                except Exception as e:
                    txt, think, meta, err = '', '', {'model': model}, f'{type(e).__name__}: {e}'
                stop.set(); th.join(timeout=10)
                parsed, perr = extract_json(txt)
                defects = parsed.get('defects') if isinstance(parsed, dict) else None
                rec = {'task': 'T5', 'model': model, 'item': item['id'], 'seed': seed,
                       'error': err, 'parse_error': perr,
                       'n_defects': len(defects) if isinstance(defects, list) else None,
                       'meta': meta | memout, 'defects': defects, 'raw_response': txt,
                       'thinking_chars': len(think)}
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                print(f"-> n={rec['n_defects']} {meta.get('wall_s')}s {err or perr or ''}", flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
