#!/usr/bin/env python3
"""Minimal ollama /api/chat client with timing capture. stdlib only."""
import json, time, urllib.request, urllib.error

# Two instances run side by side. The system service (11434, v0.17.6) holds the
# models the first 127 cells were measured against and is left alone; a
# user-space install (11435, v0.32.15) serves qwen3.8 and gemma4, which 0.17.6
# refuses with a 412. Set OLLAMA_PORT to pick one.
import os
HOST = f"http://127.0.0.1:{os.environ.get('OLLAMA_PORT', '11434')}"


def host():
    return f"http://127.0.0.1:{os.environ.get('OLLAMA_PORT', '11434')}"


def server_version():
    try:
        with urllib.request.urlopen(host() + '/api/version', timeout=10) as r:
            return json.loads(r.read()).get('version')
    except Exception:
        return None

def chat(model, messages, num_ctx=32768, temperature=0.0, seed=42,
         num_predict=-1, timeout=3600, think=None, extra_options=None, tools=None):
    """Return (text, meta). meta carries ollama's own timing counters."""
    options = {'num_ctx': num_ctx, 'temperature': temperature, 'seed': seed,
               'num_predict': num_predict}
    if extra_options:
        options.update(extra_options)
    payload = {'model': model, 'messages': messages, 'stream': False,
               'options': options}
    if think is not None:
        payload['think'] = think
    if tools:
        payload['tools'] = tools
    req = urllib.request.Request(
        host() + '/api/chat', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # ollama puts the actual reason in the body; without it a 500 is
        # indistinguishable from any other failure
        try:
            body = e.read().decode()[:400]
        except Exception:
            body = '(no body)'
        raise RuntimeError(f'HTTP {e.code}: {body}') from None
    wall = time.monotonic() - t0
    msg = d.get('message', {})
    ns = 1e9
    pe_n, pe_d = d.get('prompt_eval_count', 0), d.get('prompt_eval_duration', 0)
    ev_n, ev_d = d.get('eval_count', 0), d.get('eval_duration', 0)
    meta = {
        'model': model,
        'wall_s': round(wall, 2),
        'prompt_tokens': pe_n,
        'output_tokens': ev_n,
        'load_s': round(d.get('load_duration', 0) / ns, 2),
        'prefill_tok_s': round(pe_n / (pe_d / ns), 1) if pe_d else None,
        'decode_tok_s': round(ev_n / (ev_d / ns), 1) if ev_d else None,
        'ttft_s': round((d.get('load_duration', 0) + pe_d) / ns, 2),
        'done_reason': d.get('done_reason'),
        'tool_calls': msg.get('tool_calls'),
    }
    return msg.get('content', ''), msg.get('thinking') or '', meta

def same_model(reported, requested):
    """True when two model tags name the same model.

    `/api/ps` reports `gemma4:latest` for a model requested as `gemma4`, so an
    exact-string filter silently returns no footprint at all.
    """
    if not reported or not requested:
        return False
    return reported.removesuffix(':latest') == requested.removesuffix(':latest')


def ps():
    """Currently loaded models and their reported footprint."""
    with urllib.request.urlopen(host() + '/api/ps', timeout=30) as r:
        return json.loads(r.read())

def unload(model):
    req = urllib.request.Request(
        host() + '/api/chat',
        data=json.dumps({'model': model, 'messages': [], 'keep_alive': 0}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.URLError:
        pass
