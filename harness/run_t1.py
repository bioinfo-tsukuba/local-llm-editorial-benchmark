#!/usr/bin/env python3
"""T1: submission-guideline compliance check. Runs one (model, manuscript, seed) cell
per invocation loop and writes a JSON record per cell to results/t1/.

Usage: run_t1.py [--models m1,m2] [--manuscripts MS-A,MS-B] [--seeds 42,43,44]
                 [--num-ctx 32768] [--dry-run]
"""
import argparse, json, os, pathlib, re, sys, threading, time, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ollama_client as oc
from prompts import build_t1, build_t1b


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

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'results' / 't1'

DEFAULT_MODELS = [
    'gpt-oss:20b',
    'qwen3.6:35b-a3b-q4_K_M',
    'qwen3.6:35b-a3b-q8_0',
    'qwen3.6:35b-a3b-bf16',
    'qwen3.5:35b-a3b-bf16',
    'qwen3.5:122b-a10b-q4_K_M',
    'gpt-oss:120b',
    'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0',
    'glm-4.5-air:q4',
]


def available_models():
    """Model tags present on the instance selected by OLLAMA_PORT.

    Names are returned both bare and with an explicit :latest so callers can
    match either spelling -- `ollama list` prints `gemma4:latest` for a model
    pulled as `gemma4`.
    """
    import subprocess
    port = os.environ.get('OLLAMA_PORT', '11434')
    env = dict(os.environ)
    env['OLLAMA_HOST'] = f'127.0.0.1:{port}'
    binary = 'ollama'
    if port == '11435':
        binary = '/home/dgx1/.local/ollama-new/bin/ollama'
        env['OLLAMA_MODELS'] = '/home/dgx1/.local/ollama-new-models'
    out = subprocess.run([binary, 'list'], capture_output=True, text=True, env=env).stdout
    names = {l.split()[0] for l in out.splitlines()[1:] if l.strip()}
    return names | {n.removesuffix(':latest') for n in names}


def is_available(model, have):
    return model in have or f'{model}:latest' in have


def think_for(model, mode):
    """Resolve the reasoning-effort argument for a model."""
    if mode == 'none':
        return None
    if mode != 'auto':
        return mode
    return 'low' if 'gpt-oss' in model else None


def slug(model):
    return re.sub(r'[^A-Za-z0-9._-]', '_', model)


def mem_sampler(stop, out, model=None):
    """Sample system memory + ollama's reported footprint while a call is running.

    `model` filters /api/ps to the model under test: a previously used model can still
    be resident when the next call starts, and taking the max over everything loaded
    would report the wrong model's footprint.
    """
    peak_used = 0
    peak_vram = 0
    while not stop.is_set():
        try:
            mi = {}
            for line in open('/proc/meminfo'):
                k, v = line.split(':')
                mi[k] = int(v.split()[0])
            used = (mi['MemTotal'] - mi['MemAvailable']) // 1024  # MiB
            peak_used = max(peak_used, used)
        except Exception:
            pass
        try:
            for m in oc.ps().get('models', []):
                if model and not oc.same_model(m.get('model'), model):
                    continue
                peak_vram = max(peak_vram, m.get('size_vram', 0))
        except Exception:
            pass
        time.sleep(2.0)
    out['peak_mem_used_mib'] = peak_used
    out['peak_size_vram_mib'] = peak_vram // (1024 * 1024)


def repair_json(s):
    """Fix the malformed-JSON shapes models actually produce.

    Observed: two adjacent string literals in a value position with no comma between
    them ('"...300 dpi resolution..." "The format of the graphical abstract..."'), which
    is what a model emits when it means to continue a quotation. Unescaped quote-space-
    quote outside a string is always malformed, so merging the two literals is safe.
    Also strips trailing commas before a closing brace or bracket.
    """
    s = re.sub(r'(?<!\\)"(\s+)"', r'\1', s)
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    return s


def extract_json(text):
    """Pull the findings object out of a possibly fence-wrapped / chatty response."""
    if not text:
        return None, 'empty response'
    s = text.strip()
    # Models imported from a bare GGUF with `ollama create` lose the chat template's
    # handling of reasoning tags, so glm-4.5-air:q4 emits literal <think>...</think> in
    # the content instead of in the separate `thinking` field. Strip those blocks, plus a
    # stray unmatched closing tag, before looking for JSON.
    s = re.sub(r'(?is)<think>.*?</think>', '', s)
    s = re.sub(r'(?i)</?think>', '', s).strip()
    s = re.sub(r'^```(?:json)?\s*', '', s)
    s = re.sub(r'\s*```$', '', s).strip()
    for cand in (s, repair_json(s)):
        try:
            return json.loads(cand), None if cand is s else 'repaired'
        except Exception:
            pass
    s = repair_json(s)
    # first balanced {...} containing "findings"
    i = s.find('{')
    while i != -1:
        depth = 0
        for j in range(i, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    cand = s[i:j + 1]
                    if 'findings' in cand:
                        try:
                            return json.loads(cand), None
                        except Exception:
                            break
                    break
        i = s.find('{', i + 1)
    # bare array fallback
    m = re.search(r'\[\s*\{.*\}\s*\]', s, re.S)
    if m:
        try:
            return {'findings': json.loads(m.group(0))}, None
        except Exception:
            pass
    # Last resort: salvage the individual objects a model produced before it abandoned
    # the schema. GLM-4.7-Flash was observed to stop emitting JSON partway through an
    # array and continue in prose. The salvaged items are real answers and should not be
    # thrown away, but the cell is flagged 'salvaged' so it is never mistaken for a clean
    # response -- holding a schema is itself a capability an editorial pipeline needs.
    objs = []
    i = 0
    while i < len(s):
        if s[i] != '{':
            i += 1
            continue
        depth, j, instr, esc = 0, i, False, False
        while j < len(s):
            ch = s[j]
            if instr:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    instr = False
            elif ch == '"':
                instr = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        blob = s[i:j + 1]
        parsed_ok = False
        try:
            o = json.loads(blob)
            if isinstance(o, dict) and len(o) > 1:
                objs.append(o)
                parsed_ok = True
        except Exception:
            pass
        # Advance past the object only when it parsed. The document's outermost brace is
        # itself unbalanced in a schema break, so skipping to its (non-existent) close
        # would consume the whole response and salvage nothing.
        i = j + 1 if parsed_ok else i + 1
    if objs:
        return {'__salvaged__': objs}, 'salvaged'
    return None, 'unparseable'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', default=','.join(DEFAULT_MODELS))
    ap.add_argument('--manuscripts', default='MS-A,MS-B')
    ap.add_argument('--seeds', default='42,43,44')
    ap.add_argument('--num-ctx', type=int, default=65536,
                    help='must leave room for num_predict on top of the ~12k prompt: at '
                         'num_ctx=32768 only ~20k output tokens fit, so a 24576 cap can '
                         'never be reached and the model is truncated by the context '
                         'window instead')
    ap.add_argument('--num-predict', type=int, default=24576,
                    help='hard cap on generated tokens (thinking included) so a looping '
                         'reasoning model cannot run unbounded')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--variant', default='a', choices=['a', 'b'],
                    help="'a' = free-form request (default); 'b' = externally supplied "
                         "eight-area checklist, which stops the comparison from being a "
                         "proxy for how much a model reasons unprompted")
    ap.add_argument('--timeout', type=int, default=3600,
                    help='client-side seconds per request; a cell that exceeds it is '
                         'recorded as a timeout, which is a property of the budget, '
                         'not of the model')
    ap.add_argument('--think', default='auto',
                    help="reasoning effort passed to ollama. 'auto' (default) sends "
                         "'low' to gpt-oss models and leaves every other model at its "
                         "own default: at its default effort gpt-oss spends the entire "
                         "16k token budget on reasoning and returns no answer at all "
                         "(done_reason=length, 75k characters of thinking, empty "
                         "content). Use 'none' to send nothing.")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    guidelines = (ROOT / 'data/guidelines/bppb_instructions_clean.txt').read_text()
    have = available_models()

    models = [m for m in a.models.split(',') if m]
    for model in models:
        if not is_available(model, have):
            print(f'[skip] {model}: not pulled yet', flush=True)
            continue
        for ms in a.manuscripts.split(','):
            manuscript = (ROOT / f'data/manuscripts/{ms}.md').read_text()
            msgs = (build_t1 if a.variant == 'a' else build_t1b)(guidelines, manuscript)
            for seed in [int(s) for s in a.seeds.split(',')]:
                think_arg = think_for(model, a.think)
                tsuf = '' if a.think == 'auto' else f'__think-{think_arg or "default"}'
                vsuf = '' if a.variant == 'a' else f'__variant-{a.variant}'
                f = OUT / f'{slug(model)}__{ms}__seed{seed}{tsuf}{vsuf}.json'
                if f.exists() and not a.overwrite:
                    print(f'[have] {f.name}', flush=True)
                    continue
                if a.dry_run:
                    print(f'[dry ] {f.name}  prompt_chars={sum(len(m["content"]) for m in msgs)}', flush=True)
                    continue
                print(f'[run ] {f.name}', flush=True, end=' ')
                memout, stop = {}, threading.Event()
                th = threading.Thread(target=mem_sampler, args=(stop, memout, model),
                                      daemon=True)
                th.start()
                err = None
                try:
                    txt, think, meta = oc.chat(model, msgs, num_ctx=a.num_ctx, seed=seed,
                                               num_predict=a.num_predict, think=think_arg,
                                               timeout=a.timeout)
                except Exception as e:
                    txt, think, meta, err = '', '', {'model': model}, f'{type(e).__name__}: {e}'
                stop.set(); th.join(timeout=10)
                parsed, perr = extract_json(txt)
                rec = {
                    'task': 'T1', 'variant': a.variant,
                    'model': model, 'manuscript': ms, 'seed': seed,
                    'num_ctx': a.num_ctx, 'num_predict': a.num_predict,
                    'timeout_s': a.timeout,
                    'think': think_arg, 'error': err, 'parse_error': perr,
                    'n_findings': len(parsed.get('findings', [])) if parsed else None,
                    'meta': meta | memout,
                    'findings': parsed.get('findings') if parsed else None,
                    'raw_response': txt,
                    'thinking_chars': len(think),
                }
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                print(f"-> n={rec['n_findings']} {meta.get('wall_s')}s "
                      f"prefill={meta.get('prefill_tok_s')} decode={meta.get('decode_tok_s')} "
                      f"vram={memout.get('peak_size_vram_mib')}MiB {err or perr or ''}", flush=True)
        oc.unload(model)


if __name__ == '__main__':
    main()
