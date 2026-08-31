#!/usr/bin/env python3
"""Verify the manuscript's numeric claims against the measurements.

Written after an audit found three claims that had been correct when written
and became wrong as the study grew: a characters-per-token ratio measured on
one input and stated as a property of the corpus; a count of model conditions
from an early snapshot; and a decode-share range taken from the well-behaved
models. All three shared one mechanism — a statistic computed over whichever
subset was to hand, written as a property of the whole.

Anything phrased as "N of M" expires when M changes. This script recomputes
those quantities from results/ and fails if the manuscript disagrees, so the
expiry is caught rather than published.

Usage: python3 harness/check_claims.py [RESULTS_DIR]
"""
import csv, glob, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results'
# The paper lives in BPPB-special-issue-paper/ in the working repository and in
# paper/ in the public release, which is assembled by harness/make_public_release.py.
# Resolving it here is what lets these checkers run in both trees.
PAPER = (ROOT / 'BPPB-special-issue-paper' if (ROOT / 'BPPB-special-issue-paper').is_dir()
         else ROOT / 'paper')
MS = (PAPER / 'manuscript.md').read_text()

fails, notes = [], []


def claim(label, present_in_text, actual, ok):
    mark = 'ok  ' if ok else 'FAIL'
    print(f'{mark} {label:<44} manuscript: {present_in_text:<18} measured: {actual}')
    if not ok:
        fails.append(label)


def t1_cells(ms='MS-A'):
    return [f for f in glob.glob(str(RES / 't1' / '*.json')) if ms in f]


def summary(name):
    p = RES / f'{name}_summary.csv'
    return list(csv.DictReader(p.open())) if p.exists() else []


# --- counts that expire when the population grows -------------------------
n41 = len(t1_cells())
stated = re.findall(r'(\d+) (?:model )?conditions on the defective manuscript|'
                    r'every one of the (\d+) model', MS)
stated = {x for pair in stated for x in (pair if isinstance(pair, tuple) else (pair,)) if x}
claim('T1 conditions on the defective manuscript',
      ','.join(sorted(stated)) or 'not stated', n41,
      stated == {str(n41)} or not stated)

total = sum(len(glob.glob(str(RES / t / '*.json')))
            for t in ('t1 t1c t2 t3refs t3ja t4abs t4ph t5 t6c t6d t7 t8'.split()))
# strict: the manuscript must state exactly this number, in both places it appears
stated_totals = set(re.findall(r'(\d{3}) (?:measured )?conditions', MS))
claim('total measured conditions',
      ','.join(sorted(stated_totals)) or '?', total,
      stated_totals == {str(total)})

# Superseded: the manuscript no longer says "failed by N of M tool-capable models",
# a phrasing that implied a no-tool condition T8 never ran. The replacement claims
# are checked below ("T8 models answering 4/4 and models never calling a tool" and
# "T1 conditions reporting the abbreviation violation"). Kept as a note so the
# underlying count stays visible in the output.
t8 = summary('t8')
bad = [r for r in t8 if not str(r.get('abbrev_correct', '')).startswith('4')]
notes.append(f'T8 abbreviation: {len(bad)} of {len(t8)} models did not reach 4/4')

# --- ranges that must not be quoted from a favourable subset ---------------
shares, big = [], []
for f in glob.glob(str(RES / 't1' / '*.json')):
    m = (json.load(open(f)).get('meta') or {})
    if not all(m.get(k) for k in ('output_tokens', 'prefill_tok_s', 'decode_tok_s', 'prompt_tokens')):
        continue
    pf = m['prompt_tokens'] / m['prefill_tok_s']
    dc = m['output_tokens'] / m['decode_tok_s']
    shares.append((dc / (pf + dc) * 100, m['output_tokens']))
if shares:
    b = [s for s, o in shares if o > 5000]
    _fl = ' '.join(MS.split())
    _rng = f'{min(b):.0f}\u2013{max(b):.0f}%'
    claim('decode share, cells with >5k output',
          _rng if _rng in _fl else 'other',
          f'{_rng} (n={len(b)} of {len(shares)})',
          _rng in _fl and f'{len(b)} of the {len(shares)} T1' in _fl)

# --- prompt-token counts are tokenizer-dependent, never a single number ----
tok = {}
for f in glob.glob(str(RES / 't2' / '*.json')):
    d = json.load(open(f)); m = d.get('meta') or {}
    if m.get('prompt_tokens'):
        tok[d['model']] = m['prompt_tokens']
if tok:
    lo, hi = min(tok.values()), max(tok.values())
    claim('T2 prompt tokens (range, not a value)',
          f'{lo:,} to {hi:,}' if f'{lo:,} to {hi:,}' in MS else '?',
          f'{lo:,}–{hi:,} over {len(tok)} models', f'{lo:,} to {hi:,} tokens' in MS)
    if hi / lo > 1.05:
        notes.append(f'T2 prompt length varies {hi/lo:.2f}x across tokenizers; '
                     'never state it as one number')

# --- word counts of the inputs --------------------------------------------
for path, pat in [('data/manuscripts/MS-A.md', r'MS-A \(([\d,]+) words\)'),
                  ('data/guidelines/bppb_instructions_clean.txt', r'\(([\d,]+) words, [\d,]+\n?tokens\)')]:
    m = re.search(pat, MS)
    if not m:
        continue
    stated = int(m.group(1).replace(',', ''))
    actual = len((ROOT / path).read_text().split())
    claim(f'word count of {pathlib.Path(path).name}', f'{stated:,}', f'{actual:,}', stated == actual)

# --- the deterministic baseline, run rather than trusted -----------------
import subprocess as _sp
try:
    _out = _sp.run([sys.executable, str(ROOT / 'harness/deterministic_check.py')],
                   capture_output=True, text=True, timeout=120).stdout
    _m = re.search(r'(\d+)/40', _out)
    _measured = int(_m.group(1)) if _m else None
except Exception as _e:
    _measured, _out = None, str(_e)
if _measured is None:
    print(f'{"deterministic baseline":<44} could not run the checker: {_out[:60]}')
    fails.append('deterministic checker did not run')
else:
    claim('deterministic baseline (run, not quoted)',
          re.search(r'\*\*(\d+)/40\*\*', MS).group(1) + '/40' if re.search(r'\*\*\d+/40\*\*', MS) else '?',
          f'{_measured}/40', f'**{_measured}/40**' in MS)

# --- the difficulty split, and the values derived from it ----------------
import json as _json
diff = _json.loads((ROOT / 'data/groundtruth/MS-A_difficulty.json').read_text())
nE, nH = len(diff['easy']), len(diff['hard'])
claim('EASY / HARD denominators',
      (lambda m: m.group(0)[:24] if m else '?')(
          re.search(r'(\d+) EASY\b.*?(\d+) HARD\b', MS, re.S)),
      f'{nE} EASY / {nH} HARD',
      f'{nE} EASY' in MS and f'{nH} HARD' in MS and f'EASY ({nE})' in MS and f'HARD ({nH})' in MS)

# --- Figure 6 comparisons must match what the manuscript says -------------
spec = _json.loads((ROOT / 'data/score_change_comparisons.json').read_text())


def _detected(model, variant):
    for r in summary('t1'):
        if (r.get('model') == model and r.get('manuscript') == 'MS-A'
                and (r.get('variant') or 'a') == variant):
            return float(r['detected'])
    return None


for c in spec['comparisons']:
    if c.get('effect_from'):
        continue
    a, b = _detected(**c['from']), _detected(**c['to'])
    if a is None or b is None:
        print(f'  ! {c["label"]}: a condition is missing from results')
        continue
    notes.append(f'{c["label"]}: {b - a:+g}')

# --- the inference configuration the Methods states -----------------------
# Added after the re-run: v1 had accumulated three different timeout values and
# two context sizes, and one slow cell had been granted a 10800 s exception. The
# Methods now claims a uniform 3600 s budget and a per-task context size, so both
# have to be recomputed rather than trusted.
CTX = {'t1': 65536, 't1c': 65536, 't2': 131072, 't3refs': 32768, 't3ja': 32768,
       't4abs': 32768, 't4ph': 32768, 't5': 16384, 't6c': 65536, 't6d': 65536,
       't7': 65536, 't8': 32768}
budgets, ctx_bad, no_budget = set(), [], []
for task, want in CTX.items():
    for f in glob.glob(str(RES / task / '*.json')):
        try:
            d = json.loads(pathlib.Path(f).read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        t = d.get('timeout_s')
        if t is None:
            no_budget.append(f'{task}/{pathlib.Path(f).name}')
        else:
            budgets.add(t)
        got = d.get('num_ctx')
        if got is not None and got != want:
            ctx_bad.append(f'{task}/{pathlib.Path(f).name}: {got} != {want}')

claim('uniform wall-clock budget, no exception',
      '3600' if '3,600 s' in MS else 'not stated',
      ','.join(str(b) for b in sorted(budgets)) or 'none recorded',
      budgets <= {3600})
if no_budget:
    notes.append(f'{len(no_budget)} cell(s) record no timeout_s (pre-re-run harness); every reported cell must record 3600 before submission')
claim('per-task num_ctx as stated in Methods', 'see Methods',
      'all match' if not ctx_bad else f'{len(ctx_bad)} differ: ' + '; '.join(ctx_bad[:3]),
      not ctx_bad)

# --- the partition of what the checker cannot decide ----------------------
# The manuscript once said "ten items the checker cannot reach" where the checker
# reports nine, and derived a five-way split from the wrong total. The partition
# now lives in data/ and its item set must equal the checker's own output.
import subprocess as _sp
_out = _sp.run(['python3', str(ROOT / 'harness/deterministic_check.py')],
               capture_output=True, text=True).stdout
_unreach = set(re.findall(r'\bV\d{2}\b', _out.split('判定不能')[-1]))
_part = _json.loads((ROOT / 'data/groundtruth/MS-A_unreachable_partition.json').read_text())
_ids = {i['id'] for i in _part['items']}
claim('partition covers exactly what the checker cannot decide',
      f'{len(_ids)} classified', f'{len(_unreach)} unreachable',
      _ids == _unreach)
_n_llm = sum(1 for i in _part['items'] if i['class'] == 'language_model')
_words = {4: 'four', 5: 'five', 3: 'three', 6: 'six', 7: 'seven'}
# every phrasing of "N of the forty" must agree; the Conclusion carried "five of
# the forty items" across a line break after the Results had been corrected to four
_flat = ' '.join(MS.split())
_said = set(re.findall(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b'
                       r'(?: of| of the) forty (?:violations|items)', _flat))
claim('violations genuinely requiring a language model',
      ','.join(sorted(_said)) or 'not stated',
      f'{_words.get(_n_llm, _n_llm)} ({_n_llm})',
      _said == {_words.get(_n_llm)})
claim('count of violations the checker cannot decide',
      'nine' if 'nine violations the\nchecker cannot decide' in MS
               or 'nine violations the checker cannot decide' in MS else 'other',
      f'{len(_unreach)}', len(_unreach) == 9)

# --- the zero-detection conditions Figure 3 shows as empty rows ------------
_zero = [r for r in summary('t1')
         if r.get('manuscript') == 'MS-A' and str(r.get('detected')) == '0']
_starved = sum(1 for r in _zero if (r.get('error') or '').startswith('empty response'))
_fl0 = ' '.join(MS.split())
claim('conditions detecting no violation',
      f'{len(_zero)}' if f'{len(_zero)} of the' in _fl0 else 'other',
      f'{len(_zero)} ({_starved} returned an empty response)',
      f'{len(_zero)} of the' in _fl0 and 'detected no violation at all' in _fl0)
_ncond = len([r for r in summary('t1') if r.get('manuscript') == 'MS-A'])
_fl1 = ' '.join(MS.split())
claim('model conditions in Figure 3',
      f'{_ncond}' if f'all {_ncond} model conditions' in _fl1 else 'other',
      _ncond,
      f'all {_ncond} model conditions' in _fl1
      and f'{_ncond} conditions' in _fl1)

# --- claims added for the post-re-run reconciliation ----------------------
# Each of these is transcribed into the manuscript and moves when the matrix is
# re-measured. Listed in docs/11-post-rerun-checklist.md.
_ms_a = [r for r in summary('t1') if r.get('manuscript') == 'MS-A']
_flatms = ' '.join(MS.split())

if _ms_a:
    _best = max(_ms_a, key=lambda r: int(r['detected']))
    claim('best single model on T1',
          '34 of 40' if 'detected 34 of 40' in _flatms or '34 of the 40' in _flatms else 'other',
          f"{_best['detected']}/40 by {_best['model']} ({_best.get('variant') or 'a'})",
          f"{_best['detected']} of 40" in _flatms or f"{_best['detected']} of the 40" in _flatms)

    # the violation no model condition found -- the "checker alone catches it" claim
    _all_ids = sorted({i for r in _ms_a for i in (r.get('missed_ids') or '').split(',') if i})
    _never = [i for i in _all_ids
              if all(i in (r.get('missed_ids') or '') for r in _ms_a)]
    claim('violations found by no model condition', 'V16 (table numbering)',
          ','.join(_never) or 'none', _never == ['V16'])

    # the journal-abbreviation violation without a tool
    _v37 = sum(1 for r in _ms_a if 'V37' not in (r.get('missed_ids') or ''))
    claim('T1 conditions reporting the abbreviation violation',
          '17 of 48' if '17 of the 48 conditions' in _flatms else 'other',
          f'{_v37} of {len(_ms_a)}',
          f'{_v37} of the {len(_ms_a)} conditions' in _flatms)

_t8 = summary('t8')
if _t8:
    _ok = [r for r in _t8 if str(r.get('abbrev_correct', '')).startswith('4')]
    _none = [r for r in _t8 if str(r.get('n_tool_calls')) == '0']
    claim('T8 models answering 4/4 and models never calling a tool',
          '7 of 15; four never call' if 'and\n7 return the correct abbreviation' in MS
          or '7 return the correct abbreviation' in _flatms else 'other',
          f'{len(_ok)} of {len(_t8)} at 4/4; {len(_none)} issued no tool call',
          f'{len(_ok)} return the correct abbreviation' in _flatms)

_t2 = summary('t2')
if _t2:
    _bestr = max(_t2, key=lambda r: int(r['matched'] or 0))
    claim('peer-review points recovered',
          '7 of the 12' if '7 of the 12' in _flatms else 'other',
          f"{_bestr['matched']} of {_bestr['n_reference_points']} by {_bestr['model']}",
          f"{_bestr['matched']} of the {_bestr['n_reference_points']}" in _flatms)

# --- the size-score correlation, read from what the figure computed ---------
_ds = ROOT / 'results' / 'derived_stats.json'
if _ds.exists():
    _st = _json.loads(_ds.read_text())['size_vs_score']
    _rs = [v['spearman'] for v in _st.values()]
    _lo, _hi, _mx = min(_rs), max(_rs), max(abs(x) for x in _rs)
    _flat2 = ' '.join(MS.split())
    claim('Spearman range across the eight tasks',
          (re.search(r'coefficients lie between [-\u2212+\d.]+\s*and [-\u2212+\d.]+', _flat2)
           or re.search(r'never exceeded [\d.]+ in magnitude', _flat2)
           or type('x', (), {'group': lambda s: 'not stated'})()).group(),
          f'{_lo:+.2f} to {_hi:+.2f}, max |r| {_mx:.2f}',
          f'{_mx:.2f}' in _flat2 and f'{abs(_lo):.2f}' in _flat2 and f'{_hi:.2f}' in _flat2
          # the Abstract states the bound separately and drifted from the Results once
          and (f'|rho| <= {_mx:.2f}' in _flat2 or 'rho' not in _flat2))
else:
    notes.append('results/derived_stats.json absent; run make_paper_figures.py '
                 'before trusting the size-correlation claims')

# --- the item-set sizes the Methods now states -----------------------------
_sets = [('data/t3/refs_input.json', 8, 'T3 references'),
         ('data/t3/ja_questions.json', 10, 'T3 Japanese questions'),
         ('data/t4/absent_rules.json', 8, 'T4 guideline questions'),
         ('data/t4/phantom_elements.json', 5, 'T4 phantom elements'),
         ('data/t8/items.json', 8, 'T8 references')]
_bad = []
for rel, stated, label in _sets:
    n = len(_json.loads((ROOT / rel).read_text())['items'])
    if n != stated:
        _bad.append(f'{label}: file has {n}, Methods says {stated}')
claim('item-set sizes stated in the Methods', 'see Methods',
      'all match' if not _bad else '; '.join(_bad), not _bad)
_t4 = _json.loads((ROOT / 'data/t4/absent_rules.json').read_text())['items']
_ans = sum(1 for i in _t4 if i['answerable'])
claim('T4 answerable / unanswerable split', '4 and 4',
      f'{_ans} answerable, {len(_t4) - _ans} not', _ans == 4 and len(_t4) - _ans == 4)
_t8i = _json.loads((ROOT / 'data/t8/items.json').read_text())['items']
_nf = sum(1 for i in _t8i if i['expect'].get('found') is False)
_mm = sum(1 for i in _t8i if i['expect'].get('mismatch'))
claim('T8 unresolvable and mismatched references', 'one and two',
      f'{_nf} unresolvable, {_mm} mismatched', _nf == 1 and _mm == 2)

# --- how many conditions were repeated at more than one seed ---------------
_by = {}
for r in summary('t1'):
    _by.setdefault((r.get('model'), r.get('manuscript'), r.get('variant') or 'a'),
                   set()).add(r.get('seed'))
_rep = {k for k, v in _by.items() if len(v) > 1}
_models = sorted({k[0] for k in _rep})
_flat3 = ' '.join(MS.split())
_words15 = {15: 'Fifteen', 5: 'Five', 8: 'Eight', 7: 'seven'}
claim('conditions repeated at more than one seed',
      f'{len(_rep)} over {len(_models)}'
      if f'{_words15.get(len(_rep), len(_rep))} conditions over' in _flat3 else 'other',
      f'{len(_rep)} conditions over {len(_models)} models',
      f'{_words15.get(len(_rep), len(_rep))} conditions over' in _flat3
      and all(m in _flat3 for m in _models))

# --- the T5 band comparison and its permutation test -----------------------
import itertools as _it, statistics as _st
_inv = {m['model']: m['size_gb']
        for m in _json.loads((ROOT / 'data/model_inventory.json').read_text())['models']}
_t5 = summary('t5')
if _t5:
    _lo = [int(r['detected']) for r in _t5 if 17 <= _inv.get(r['model'], 0) <= 38]
    _hi = [int(r['detected']) for r in _t5 if _inv.get(r['model'], 0) >= 62]
    if _lo and _hi:
        _d = _st.mean(_lo) - _st.mean(_hi)
        _pool, _n = _lo + _hi, len(_lo)
        _ge = sum(1 for c in _it.combinations(range(len(_pool)), _n)
                  if _st.mean([_pool[i] for i in c])
                  - _st.mean([_pool[i] for i in range(len(_pool)) if i not in c]) >= _d)
        _p = _ge / sum(1 for _ in _it.combinations(range(len(_pool)), _n))
        _flat5 = ' '.join(MS.split())
        claim('T5 band difference and permutation p',
              (re.search(r'difference of [\d.]+ points at an exact permutation \*p\* of [\d.]+',
                         _flat5) or type('x', (), {'group': lambda s: 'not stated'})()).group(),
              f'{_d:.2f} points, p = {_p:.3f}',
              f'{_d:.2f} points' in _flat5 and f'{_p:.3f}' in _flat5)

# --- the two MS-C items the Discussion singles out --------------------------
_t6 = summary('t6c')
if _t6:
    _msc = _json.loads((ROOT / 'data/groundtruth/MS-C_groundtruth.json').read_text())
    _its = _msc.get('errors') or _msc.get('items')
    _cnt = {i['id']: sum(1 for r in _t6 if i['id'] not in (r.get('missed_ids') or ''))
            for i in _its}
    _flat6 = ' '.join(MS.split())
    claim('MS-C unit-conversion item (S03) detections',
          '1 of the 17' if 'found by 1 of the 17 models' in _flat6 else 'other',
          f"{_cnt.get('S03')} of {len(_t6)}", _cnt.get('S03') == 1)
    claim('MS-C item found by no model (S06)',
          'was found by none' if 'was found by none' in _flat6 else 'other',
          f"{_cnt.get('S06')} of {len(_t6)}", _cnt.get('S06') == 0)

# --- two-node microbenchmark ------------------------------------------------
# Added after plotting the second model exposed three wrong numbers in the text:
# a prefill range that covered only the larger model, a decode change of "1.2-1.5%"
# that held for neither, and an RDMA-to-TCP ratio quoted from one of two prompt
# lengths. Every ratio the text states is now recomputed here.
_tn = ROOT / 'results' / 'twonode' / 'matrix.json'
if _tn.exists():
    import collections as _co
    _rw = _json.loads(_tn.read_text())
    _ag, _sz = _co.defaultdict(list), {}
    for _r in _rw:
        _ag[(_r['model'], _r['metric'], _r['nodes'], _r['prompt'])].append(_r['tok_s'])
        _sz[_r['model']] = _r['size_gib']
    _mean = lambda k: _st.mean(_ag[k]) if _ag.get(k) else None

    def _ratios(metric, num, den):
        out = {}
        for _m in _sz:
            rs = []
            for _p in sorted({k[3] for k in _ag if k[0] == _m and k[1] == metric}):
                a_, b_ = _mean((_m, metric, num, _p)), _mean((_m, metric, den, _p))
                if a_ and b_:
                    rs.append(a_ / b_)
            if rs:
                out[_m] = (min(rs), max(rs), len(rs))
        return out

    _flatn = ' '.join(MS.split())
    _pf = _ratios('prefill', 'TWO', 'ONE')
    _big = max(_sz, key=lambda m: _sz[m]); _small = min(_sz, key=lambda m: _sz[m])
    _all = (min(v[0] for v in _pf.values()), max(v[1] for v in _pf.values()))
    claim('two-node prefill gain, both models',
          '1.5-1.8x' if '1.5–1.8×' in _flatn or '1.5-1.8x' in _flatn else 'other',
          f'{_all[0]:.2f}-{_all[1]:.2f}x over {len(_pf)} models',
          round(_all[0], 1) == 1.5 and round(_all[1], 1) == 1.8)
    claim('two-node prefill gain, per model',
          f'{_sz[_big]:.2f} GiB: 1.64-1.77x; {_sz[_small]:.2f} GiB: 1.54-1.65x',
          f'{_pf[_big][0]:.2f}-{_pf[_big][1]:.2f}x ({_pf[_big][2]} lengths); '
          f'{_pf[_small][0]:.2f}-{_pf[_small][1]:.2f}x ({_pf[_small][2]})',
          f'{_pf[_big][0]:.2f}–{_pf[_big][1]:.2f}×' in _flatn
          and f'{_pf[_small][0]:.2f}–{_pf[_small][1]:.2f}×' in _flatn)
    _dc = _ratios('decode', 'TWO', 'ONE')
    _pct = lambda v: ((v[0] - 1) * 100, (v[1] - 1) * 100)
    _sl, _sh = _pct(_dc[_small]); _bl, _bh = _pct(_dc[_big])
    claim('two-node decode change, per model',
          f'{_sz[_small]:.2f} GiB: 1.5-1.9%; {_sz[_big]:.2f} GiB: 3.5-17.5%',
          f'{_sl:.1f}-{_sh:.1f}% and {_bl:.1f}-{_bh:.1f}%',
          f'{_sl:.1f}–{_sh:.1f}%' in _flatn and f'{_bl:.1f}–{_bh:.1f}%' in _flatn)
    _rt = _ratios('prefill', 'TWO', 'TWO-TCP')[_big]
    claim('RDMA-to-TCP prefill ratio',
          '3.3-3.8x' if '3.3–3.8×' in _flatn else 'other',
          f'{_rt[0]:.2f}-{_rt[1]:.2f}x over {_rt[2]} prompt lengths',
          round(_rt[0], 1) == 3.3 and round(_rt[1], 1) == 3.8)
    _tc = _ratios('prefill', 'TWO-TCP', 'ONE')[_big]
    claim('TCP two-node against one node',
          '0.46-0.54x' if '0.46–0.54×' in _flatn else 'other',
          f'{_tc[0]:.2f}-{_tc[1]:.2f}x',
          f'{_tc[0]:.2f}–{_tc[1]:.2f}×' in _flatn)

# --- the dissociations that justify reporting T3 and T4 as two measures each ---
# The Methods and the Figure 4 legend now argue the split from named models rather
# than from the fact that the sets are scored separately. Those numbers are checked
# here so the argument cannot survive a change in the data.
_diss = [('t3refs', 'fully_correct', 8, 't3ja', 'correct', 10,
          [('nemotron', 0, 8), ('gpt-oss:20b', 4, 0)]),
         ('t4abs', 'correct', 8, 't4ph', 'correctly_denied', 5,
          [('glm-4.5-air:q4', 8, 0), ('nemotron', 0, 4)])]
for _fa, _ca, _da, _fb, _cb, _db, _want in _diss:
    _A, _B = summary(_fa), summary(_fb)
    if not (_A and _B):
        continue
    _bestA = {}
    for _r in _A:
        _v = int(str(_r[_ca]).split('/')[0])
        _bestA[_r['model']] = max(_bestA.get(_r['model'], -1), _v)
    _bestB = {}
    for _r in _B:
        _v = int(str(_r[_cb]).split('/')[0])
        _bestB[_r['model']] = max(_bestB.get(_r['model'], -1), _v)
    for _m, _ea, _eb in _want:
        _ga, _gb = _bestA.get(_m), _bestB.get(_m)
        claim(f'{_fa}/{_fb} dissociation for {_m}',
              f'{_ea}/{_da} and {_eb}/{_db}',
              f'{_ga}/{_da} and {_gb}/{_db}', (_ga, _gb) == (_ea, _eb))
    _both = [m for m in _bestA if m in _bestB]
    # "agree" means the same normalised score, which is what the 14 of 17 counts;
    # a pass/fail threshold instead counts mistral-small (1.00 against 0.80) as
    # agreeing and gives 15
    _same = sum(1 for m in _both if _bestA[m] / _da == _bestB[m] / _db)
    if _fa == 't4abs':
        claim('T4 sub-sets giving the same normalised score',
              '14 of the 17' if 'agree for 14 of the 17 models' in ' '.join(MS.split())
              else 'other',
              f'{_same} of {len(_both)}', _same == 14)

print()
for n in notes:
    print('note:', n)
if fails:
    sys.exit(f'\n{len(fails)} claim(s) disagree with the measurements: ' + '; '.join(fails))
print('every checked claim matches the measurements')
