#!/usr/bin/env python3
"""Estimate KV-cache footprint per model, to answer the 96 / 128 / 256 GB question.

Weights are only part of the requirement: a real paper is ~40k tokens (measured on the
T2 preprint), and the KV cache at that length is not negligible. Config values are read
from the GGUF metadata that ollama already reports via `ollama show`.
"""
import re, subprocess, sys

MODELS = ['gpt-oss:20b', 'gpt-oss:120b', 'qwen3.6:35b-a3b-q4_K_M', 'qwen3.6:35b-a3b-q8_0',
          'qwen3.6:35b-a3b-bf16', 'qwen3.5:35b-a3b-bf16', 'qwen3.5:122b-a10b-q4_K_M',
          'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0',
          'hf.co/unsloth/GLM-4.5-Air-GGUF:UD-Q4_K_XL']
CTXS = [8192, 32768, 65536, 131072]


def show(model):
    r = subprocess.run(['ollama', 'show', model], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def num(txt, key):
    m = re.search(rf'{key}\s+([\d.]+)([KMB]?)', txt)
    if not m:
        return None
    v = float(m.group(1))
    return v * {'': 1, 'K': 1e3, 'M': 1e6, 'B': 1e9}[m.group(2)]


print(f'{"model":46s} {"params":>8s} {"quant":>10s} {"weights":>9s}  ' +
      '  '.join(f'KV@{c//1024}k' for c in CTXS))
for m in MODELS:
    t = show(m)
    if not t:
        print(f'{m:46s} (not pulled)'); continue
    params = num(t, 'parameters')
    quant = (re.search(r'quantization\s+(\S+)', t) or [None, '?'])[1]
    ctxmax = num(t, 'context length')
    # ollama reports the on-disk size via `ollama list`; use it as the weight footprint
    sz = subprocess.run(['ollama', 'list'], capture_output=True, text=True).stdout
    w = None
    for line in sz.splitlines():
        if line.startswith(m.split(':')[0]) and m.split(':')[-1] in line:
            mm = re.search(r'([\d.]+)\s*GB', line)
            if mm:
                w = float(mm.group(1))
    row = f'{m:46s} {params/1e9 if params else 0:7.1f}B {quant:>10s} '
    row += f'{w if w else float("nan"):8.1f}G '
    # KV bytes = 2 (K,V) * layers * kv_heads * head_dim * ctx * bytes_per_elem
    L = num(t, 'block_count') or num(t, 'layers')
    print(row + f'  layers={L}  ctx_max={int(ctxmax) if ctxmax else "?"}')
print('\nnote: ollama does not expose kv_head/head_dim via `ollama show`; the measured '
      'peak size_vram in the sweep results is the authoritative number and is compared '
      'against these weight sizes in the report.')
