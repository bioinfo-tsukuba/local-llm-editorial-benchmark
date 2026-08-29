#!/usr/bin/env python3
"""Measure the KV-cache cost empirically instead of computing it from config metadata.

Loads each model at several num_ctx values with a one-token request and reads the
footprint ollama reports for the loaded model. The difference between context lengths is
the KV cache (plus compute buffers), which is the part of the memory requirement that
scales with document length -- and a real paper is ~40k tokens, so it is not a rounding
error when deciding between 96, 128 and 256 GB.
"""
import json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc

ROOT = pathlib.Path(__file__).resolve().parent.parent
CTXS = [4096, 16384, 32768, 65536, 131072]
MODELS = sys.argv[1:] or [
    'gpt-oss:20b', 'qwen3.6:35b-a3b-q4_K_M', 'qwen3.6:35b-a3b-q8_0',
    'qwen3.6:35b-a3b-bf16', 'qwen3.5:122b-a10b-q4_K_M', 'gpt-oss:120b',
    'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0',
    'glm-4.5-air:q4']

rows = []
for m in MODELS:
    for ctx in CTXS:
        oc.unload(m); time.sleep(2)
        try:
            _, _, meta = oc.chat(m, [{'role': 'user', 'content': 'hi'}],
                                 num_ctx=ctx, num_predict=1, timeout=1800)
        except Exception as e:
            print(f'{m} @ {ctx}: {type(e).__name__}: {e}', flush=True)
            rows.append({'model': m, 'num_ctx': ctx, 'error': str(e)[:200]})
            continue
        loaded = [x for x in oc.ps().get('models', []) if oc.same_model(x['model'], m)]
        vram = loaded[0]['size_vram'] if loaded else None
        rows.append({'model': m, 'num_ctx': ctx,
                     'size_vram_gib': round(vram / 2**30, 2) if vram else None,
                     'load_s': meta.get('load_s')})
        print(f"{m:46s} ctx={ctx:7d} -> {rows[-1]['size_vram_gib']} GiB "
              f"(load {meta.get('load_s')}s)", flush=True)
    oc.unload(m)

# Merge rather than overwrite: this script is also invoked for a single model to fill
# in a gap (GLM-4.5-Air had to be imported under a different name), and clobbering the
# earlier sweep's results would silently discard them.
out = ROOT / 'results/kv_footprint.json'
prev = json.loads(out.read_text()) if out.exists() else []
done = {(r['model'], r.get('num_ctx', r.get('target_tokens'))) for r in rows}
merged = [r for r in prev
          if (r['model'], r.get('num_ctx', r.get('target_tokens'))) not in done] + rows
out.write_text(json.dumps(merged, indent=1))
print('\nwritten results/kv_footprint.json')
