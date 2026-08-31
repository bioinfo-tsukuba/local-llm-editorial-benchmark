#!/usr/bin/env python3
"""Cold-cache prefill/decode benchmark at realistic input lengths.

The task runs cannot be trusted for prefill speed: ollama caches the prompt prefix, and
a cell whose prefix was already seen reports an absurd figure (518,067 tok/s was
observed). Here the model is unloaded before every measurement, which drops the cache,
and the input is a slice of the real preprint so the token count is realistic rather
than synthetic filler.

Input lengths correspond to the actual editorial workloads:
  ~4k   a short Note plus the relevant part of the guidelines
  ~12k  the guidelines plus a full manuscript (task T1, measured)
  ~40k  a full paper (task T2, measured on arXiv:2512.17597)
"""
import json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = [4000, 12000, 40000]          # approximate prompt tokens
MODELS = sys.argv[1:] or [
    'gpt-oss:20b', 'qwen3.6:35b-a3b-q4_K_M', 'qwen3.6:35b-a3b-q8_0',
    'qwen3.6:35b-a3b-bf16', 'qwen3.5:35b-a3b-bf16', 'qwen3.5:122b-a10b-q4_K_M',
    'gpt-oss:120b', 'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0', 'glm-4.5-air:q4']

corpus = (ROOT / 'data/preprints/arxiv_2512.17597.txt').read_text()
words = corpus.split()

rows = []
for m in MODELS:
    for t in TARGETS:
        # ~1.3 tokens per word for this text; trimmed to the target then measured exactly
        text = ' '.join(words[:int(t / 1.3)])
        msgs = [{'role': 'user',
                 'content': 'Summarise the following text in one sentence.\n\n' + text}]
        oc.unload(m); time.sleep(3)          # drop the prompt cache
        try:
            _, _, meta = oc.chat(m, msgs, num_ctx=65536, num_predict=128,
                                 think='low' if 'gpt-oss' in m else None, timeout=3600)
        except Exception as e:
            print(f'{m} @ {t}: {type(e).__name__}: {e}', flush=True)
            rows.append({'model': m, 'target_tokens': t, 'error': str(e)[:200]})
            continue
        loaded = [x for x in oc.ps().get('models', []) if oc.same_model(x['model'], m)]
        pt = meta['prompt_tokens']
        pf = meta['prefill_tok_s']
        rows.append({'model': m, 'target_tokens': t, 'prompt_tokens': pt,
                     'prefill_tok_s': pf, 'decode_tok_s': meta['decode_tok_s'],
                     'ttft_s': meta['ttft_s'], 'load_s': meta['load_s'],
                     'prefill_only_s': round(pt / pf, 1) if pf else None,
                     'size_vram_gib': round(loaded[0]['size_vram'] / 2**30, 2) if loaded else None})
        r = rows[-1]
        print(f"{m:46s} in={pt:6d} prefill={pf:8.1f} tok/s "
              f"({r['prefill_only_s']:6.1f}s) decode={meta['decode_tok_s']:6.1f} "
              f"vram={r['size_vram_gib']}GiB", flush=True)
    oc.unload(m)

# Merge rather than overwrite: this script is also invoked for a single model to fill
# in a gap (GLM-4.5-Air had to be imported under a different name), and clobbering the
# earlier sweep's results would silently discard them.
out = ROOT / 'results/speed_bench.json'
prev = json.loads(out.read_text()) if out.exists() else []
done = {(r['model'], r.get('num_ctx', r.get('target_tokens'))) for r in rows}
merged = [r for r in prev
          if (r['model'], r.get('num_ctx', r.get('target_tokens'))) not in done] + rows
out.write_text(json.dumps(merged, indent=1))
print('\nwritten results/speed_bench.json')
