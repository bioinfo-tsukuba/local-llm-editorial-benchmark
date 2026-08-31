#!/usr/bin/env python3
"""Figures for the BPPB manuscript. All numbers are read from results/, never typed in.

Outputs 300 dpi PNGs to the paper's figures/ directory.
See issue #2 for the rationale behind each figure.
"""
import csv, json, glob, pathlib, collections, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The paper lives in BPPB-special-issue-paper/ in the working repository and in
# paper/ in the public release, which is assembled by harness/make_public_release.py.
# Resolving it here is what lets these checkers run in both trees.
PAPER = (ROOT / 'BPPB-special-issue-paper' if (ROOT / 'BPPB-special-issue-paper').is_dir()
         else ROOT / 'paper')
OUT = PAPER / 'figures'
AUX = ROOT / 'results' / 'aux-figures'   # drawn but not part of the paper
OUT.mkdir(parents=True, exist_ok=True)
# Figure text is set in Nimbus Sans (Helvetica-metric). BPPB sets body text and
# captions in Times New Roman; figure interiors are kept sans for legibility at
# 6-7 pt. For strict matching use 'Nimbus Roman' (Times-metric) instead.
FONT = 'Nimbus Sans'
plt.rcParams.update({'font.size': 8, 'font.family': FONT, 'mathtext.fontset': 'stixsans',
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.linewidth': .6, 'xtick.major.width': .6,
                     'ytick.major.width': .6, 'figure.dpi': 300})

# Nothing quantitative is written into this script. Sizes, the difficulty
# classification and the Figure 6 comparisons all live under data/ so that a figure
# cannot disagree with the record it is drawn from.
_INV = json.loads((ROOT / 'data/model_inventory.json').read_text())['models']
SIZE = {m['model']: m['size_gb'] for m in _INV}
CAPABLE = {'vision': {m['model'] for m in _INV if m['vision']},
           'tools': {m['model'] for m in _INV if m['tools']}}

SHORT = {'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0': 'GLM-4.7-Flash',
         'qwen3.5:122b-a10b-q4_K_M': 'qwen3.5:122b', 'qwen3.6:35b-a3b-q4_K_M': 'qwen3.6 q4',
         'qwen3.6:35b-a3b-q8_0': 'qwen3.6 q8', 'qwen3.6:35b-a3b-bf16': 'qwen3.6 bf16',
         'qwen3.5:35b-a3b-bf16': 'qwen3.5 bf16', 'qwen3-vl:30b-a3b-instruct': 'qwen3-vl q4',
         'qwen3-vl:30b-a3b-instruct-bf16': 'qwen3-vl bf16', 'glm-4.5-air:q4': 'GLM-4.5-Air'}
short = lambda m: SHORT.get(m, m)

# what harness/deterministic_check.py scores alone; regenerate with that script
DETERMINISTIC_BASELINE = 31

INK, MUTE, ACC, WARN, BAD = '#16202b', '#93a3b1', '#0f6b7a', '#8f6415', '#a2373a'


def _rank(a):
    order = sorted(range(len(a)), key=lambda i: a[i]); r = [0.0] * len(a); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and a[order[j + 1]] == a[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    """Rank correlation. Preferred over Pearson here: n is small and a single
    old 4B model would otherwise dominate the coefficient."""
    return float(np.corrcoef(_rank(list(x)), _rank(list(y)))[0, 1])


def rows(name):
    p = ROOT / 'results' / f'{name}_summary.csv'
    return list(csv.DictReader(p.open())) if p.exists() else []


def num(x):
    try:
        return float(str(x).split('/')[0])
    except Exception:
        return None


def best(name, field, denom):
    """Best score per model for one task, as (raw, normalised)."""
    out = {}
    for r in rows(name):
        m = r.get('model')
        v = num(r.get(field))
        if not m or v is None:
            continue
        if m not in out or v > out[m]:
            out[m] = v
    return {m: (v, v / denom) for m, v in out.items()}


# Nine scored measures across the eight tasks: T3 and T4 each contribute two, since
# each was built from two item sets that are scored separately. T4 was absent from these
# figures until the panels were counted against the eight tasks the text claims.
TASKS = [('T1 guidelines', 't1', 'detected', 40),
         ('T2 review', 't2', 'matched', 12),
         ('T3a references', 't3refs', 'fully_correct', 8),
         ('T3b Japanese rules', 't3ja', 'correct', 10),
         ('T4a guideline gaps', 't4abs', 'correct', 8),
         ('T4b absent elements', 't4ph', 'correctly_denied', 5),
         ('T5 figures', 't5', 'detected', 5),
         ('T6 consistency', 't6c', 'detected', 10),
         ('T7 category rules', 't7', 'applicable_detected', 8),
         ('T8 tool use', 't8', 'abbrev_correct', 4)]
SCORES = {label: best(f, fld, d) for label, f, fld, d in TASKS}




# ------------------------------------------------- Graphical abstract (J-STAGE)
def fig_graphical_abstract():
    """Single panel for the J-STAGE graphical abstract. Read on its own, small,
    so it says what the study did and shows one result."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    fig = plt.figure(figsize=(6.6, 2.7))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')

    def card(x, y, w, h, fc, ec):
        # borders drawn transparent: the fills already separate the three panels,
        # and the rules competed with the content at graphical-abstract size
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.6',
                                    fc=fc, ec='none', lw=0, zorder=1))

    def arrow(x1, x2, y):
        ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle='-|>', mutation_scale=13,
                                     color='#a8b6c1', lw=1.6, zorder=4))

    # -------- 1. confidential manuscripts, so the model stays in-house
    card(1, 20, 27, 62, '#f4f7f9', '#d4dde3')
    ax.text(14.5, 76, 'Manuscripts under review', ha='center', va='top',
            fontsize=8.4, fontweight='bold', color=INK)
    ax.add_patch(FancyBboxPatch((7.5, 34), 14, 30, boxstyle='round,pad=0,rounding_size=1',
                                fc='white', ec='#c2ccd4', lw=.8, zorder=2))
    for k in range(7):
        ax.plot([9.5, 19.5 if k % 3 != 2 else 16], [60 - k * 3.4] * 2,
                color='#ccd5dc', lw=1.5, solid_capstyle='round', zorder=3)
    ax.add_patch(plt.Circle((21.5, 62), 3.2, fc=BAD, lw=0, zorder=4))
    ax.text(21.5, 62, '!', ha='center', va='center', color='white',
            fontsize=8, fontweight='bold', zorder=5)
    ax.text(14.5, 32.5, 'are confidential; where policy\nforbids an external service,\n'
            'the model must run in-house',
            ha='center', va='top', fontsize=6.5, color=MUTE, linespacing=1.25)

    arrow(29.5, 34.5, 51)

    # -------- 2. what was measured
    card(36, 20, 30, 62, '#eef4f5', '#b9d2d6')
    ax.text(51, 76, 'So we measured', ha='center', va='top',
            fontsize=8.4, fontweight='bold', color=ACC)
    gx, gy, cw, ch = 39.5, 55, 1.32, 1.9
    rng = np.random.default_rng(0)
    for r in range(8):
        for c in range(17):
            on = rng.random() > .18
            ax.add_patch(plt.Rectangle((gx + c * cw, gy + r * ch), cw * .74, ch * .66,
                                       fc=ACC if on else '#dde6e8',
                                       alpha=.9 if on else 1, lw=0, zorder=3))
    _nmod = len(_INV)
    ax.text(51, 51, f'{_nmod} locally hosted language models\nacross\n8 editorial tasks',
            ha='center', va='top', fontsize=7.4, color=INK, fontweight='bold',
            linespacing=1.3)
    ax.text(51, 36, 'checking manuscripts against the rules,\nand supporting peer review',
            ha='center', va='top', fontsize=6.8, color=MUTE, linespacing=1.25)
    ax.text(51, 26.5, 'on one compact desktop workstation',
            ha='center', va='top', fontsize=6.8, color=MUTE, style='italic')

    arrow(67.5, 72.5, 51)

    # -------- 3. the finding worth one glance
    card(74, 20, 25, 62, '#fdf6e8', '#e3d3ae')
    ax.text(86.5, 76, 'What the model adds', ha='center', va='top',
            fontsize=8.4, fontweight='bold', color=WARN)
    ax.text(86.5, 69.5, 'of 40 seeded violations', ha='center', va='top',
            fontsize=6.6, color=MUTE)

    # both segments computed: the checker's score and the 40 minus it
    _base, _n = DETERMINISTIC_BASELINE, 40
    _add = _n - _base
    bx, bw, by, bh = 77.5, 19.5 / 40, 57, 7.5
    ax.add_patch(plt.Rectangle((bx, by), _base * bw, bh, fc=ACC, lw=0, zorder=3))
    ax.add_patch(plt.Rectangle((bx + _base * bw, by), _add * bw, bh, fc=WARN, lw=0,
                               zorder=3))
    ax.add_patch(plt.Rectangle((bx, by), 40 * bw, bh, fc='none', ec='#bfae83',
                               lw=.8, zorder=4))
    ax.text(bx + _base / 2 * bw, by + bh / 2, str(_base), ha='center', va='center',
            color='white', fontsize=10, fontweight='bold', zorder=5)
    ax.text(bx + (_base + _add / 2) * bw, by + bh / 2, str(_add), ha='center', va='center',
            color='white', fontsize=8.5, fontweight='bold', zorder=5)

    for k, (c, lab) in enumerate([(ACC, 'a plain script, no model'),
                                  (WARN, 'a language model')]):
        yy = 48 - k * 7.5
        ax.add_patch(plt.Rectangle((bx, yy), 2.6, 2.6, fc=c, lw=0, zorder=3))
        ax.text(bx + 4, yy + 1.3, lab, va='center', fontsize=7, color=INK, zorder=3)

    ax.text(86.5, 31, 'the model is the last\nand smallest layer',
            ha='center', va='top', fontsize=7.4, color=WARN, fontweight='bold')

    fig.savefig(OUT / 'graphical_abstract.png', bbox_inches='tight', dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 1 (concept)
def fig_concept():
    """Graphical abstract: the motivating question and the study design.
    Deliberately carries no results - those are Figures 2-5."""
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig = plt.figure(figsize=(7.4, 4.6))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')

    def card(x, y, w, h, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.4',
                                    fc=fc, ec=ec, lw=.8, zorder=1))

    def title(cx, y, t, c=INK, size=8.4):
        ax.text(cx, y, t, ha='center', va='top', fontsize=size, fontweight='bold', color=c)

    def lines(cx, y, txts, size=6.5, c=MUTE, ha='center', lh=2.45):
        for k, t in enumerate(txts):
            ax.text(cx, y - k * lh, t, ha=ha, va='top', fontsize=size, color=c)
        return y - len(txts) * lh

    def arrow(x1, x2, y):
        ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle='-|>', mutation_scale=11,
                                     color='#b6c2cb', lw=1.2, zorder=4))

    C1, C2, C3, W = 2.0, 35.0, 68.0, 30.0
    for x, t in [(C1, 'WHY'), (C2, 'WHAT WE BUILT'), (C3, 'HOW WE MEASURED')]:
        ax.text(x, 98.5, t, fontsize=7, color='#8fa0ad', fontweight='bold', va='top')

    # ============ column 1: motivation ==============================
    card(C1, 66, W, 28, '#f4f7f9', '#d4dde3')
    title(C1 + W / 2, 92, 'Journal editorial office')
    lines(C1 + W / 2, 88.3, ['manuscripts are unpublished,', 'so inference must stay local'])
    for k, (t, sub) in enumerate([('Guideline compliance', 'check a manuscript against the rules'),
                                  ('Peer-review support', 'surface points a reviewer may miss')]):
        yy = 78.0 - k * 6.4
        ax.add_patch(FancyBboxPatch((C1 + 2.5, yy), W - 5, 5.0,
                                    boxstyle='round,pad=0,rounding_size=1.0',
                                    fc='white', ec='#c9d3dc', lw=.7, zorder=2))
        ax.text(C1 + 4, yy + 3.3, t, fontsize=7.0, color=INK, va='center', zorder=3)
        ax.text(C1 + 4, yy + 1.4, sub, fontsize=5.9, color=MUTE, va='center', zorder=3)

    card(C1, 34, W, 28, '#fdf6e8', '#e3d3ae')
    title(C1 + W / 2, 60, 'How capable are they?', WARN, 9.0)
    lines(C1 + W / 2, 55.0, ['Hosted frontier models are not',
                             'an option here. What open-weight',
                             'models can do on editorial work',
                             'has not been measured.'], 6.6, INK)
    ax.text(C1 + W / 2, 41.0, 'so we measured the work itself',
            ha='center', va='top', fontsize=6.4, color=MUTE, style='italic')

    y = lines(C1 + W / 2, 29.0, ['Eight editorial tasks,',
                                 'built from real material,'], 7.2, INK)
    lines(C1 + W / 2, y - 0.8, ['run on hardware a laboratory', 'can actually put on a desk.'],
          7.2, BAD)

    # ============ column 2: the benchmark ===========================
    card(C2, 62, W, 32, '#f4f7f9', '#d4dde3')
    title(C2 + W / 2, 92, 'A benchmark from real rules and reviews')
    # Counted from the material itself. The word count was written in as 4,539, which
    # was the truncated copy of the guidelines; the complete document is longer, and a
    # figure that carries a number must not be the place it goes stale.
    _gw = len((ROOT / 'data/guidelines/bppb_instructions_clean.txt').read_text().split())
    _msa = json.loads((ROOT / 'data/groundtruth/MS-A_groundtruth.json').read_text())
    _msc = json.loads((ROOT / 'data/groundtruth/MS-C_groundtruth.json').read_text())
    _mse = json.loads((ROOT / 'data/groundtruth/MS-E_groundtruth.json').read_text())
    _t2 = json.loads((ROOT / 'data/groundtruth/T2_review_points.json').read_text())
    _t5 = json.loads((ROOT / 'data/groundtruth/T5_groundtruth.json').read_text())
    # Seeded defects are violations, so MS-E's five exempt items are not counted:
    # they are rules that deliberately do not apply. The label read 63, which was
    # 40 + 10 + 8 + those 5.
    _seeded = (len(_msa['violations']) + int(_msc.get('n_errors') or 0)
               + len(_mse['applicable_violations']))
    _figs = sum(1 for i in _t5['items'] if i['defects'])
    _fdef = sum(len(i['defects']) for i in _t5['items'])
    _checks = sum(int(x) for x in re.findall(r'(\d+) checks',
                  _msc.get('verified_by', '') + ' ' + _mse.get('verified_by', '')))
    for k, (a, b) in enumerate([("a journal's Instructions for Authors", f'{_gw:,} words'),
                                ('5 manuscripts we wrote for this study', f'{_seeded} seeded defects'),
                                ('3 published reviews of a real preprint',
                                 f"{len(_t2['points'])} reference points"),
                                (f'{_figs} figures carrying {_fdef} defects',
                                 '+ 1 compliant control')]):
        yy = 87.0 - k * 5.6
        ax.text(C2 + 2.5, yy, a, fontsize=6.3, color=INK, va='top')
        ax.text(C2 + 2.5, yy - 2.5, b, fontsize=5.8, color=ACC, va='top')
    ax.text(C2 + W / 2, 64.4, f'ground truth verified by {_checks} independent checks',
            ha='center', va='top', fontsize=6.2, color=MUTE, style='italic')

    card(C2, 8, W, 50, '#eef4f5', '#b9d2d6')
    title(C2 + W / 2, 56, 'Eight editorial tasks', size=8.2)
    tasks = [('T1', 'compliance with the guidelines'), ('T2', 'peer-review points'),
             ('T3', 'reference formatting / rule queries'), ('T4', 'resistance to hallucination'),
             ('T5', 'figures and tables (vision)'), ('T6', 'scientific self-consistency'),
             ('T7', 'rules that apply only to a category'), ('T8', 'reference checking with tools')]
    for k, (tid, desc) in enumerate(tasks):
        yy = 50.0 - k * 4.6
        ax.text(C2 + 3.0, yy, tid, fontsize=6.8, color=ACC, fontweight='bold', va='center')
        ax.text(C2 + 7.2, yy, desc, fontsize=6.3, color=INK, va='center')
    ax.text(C2 + W / 2, 11.5, 'each with a control condition where\nthe correct answer is "nothing wrong"',
            ha='center', va='center', fontsize=6.1, color=MUTE, style='italic')

    # ============ column 3: the measurement =========================
    card(C3, 58, W, 36, '#f4f7f9', '#d4dde3')
    title(C3 + W / 2, 92, 'Factors varied', size=8.2)
    gx, gy, cw, ch = C3 + 4.2, 71.5, 1.24, 1.42
    rng = np.random.default_rng(0)
    for r in range(9):
        for c in range(17):
            on = rng.random() > .18
            ax.add_patch(plt.Rectangle((gx + c * cw, gy + r * ch), cw * .78, ch * .74,
                                       fc=ACC if on else '#e3e9ed',
                                       alpha=.85 if on else 1, lw=0, zorder=3))
    # not a full crossing: which models run which task depends on capability, so the
    # grid is ragged and "17 x 8" would misdescribe it
    _cells = sum(len(glob.glob(str(ROOT / 'results' / t / '*.json')))
                 for t in 't1 t1c t2 t3refs t3ja t4abs t4ph t5 t6c t6d t7 t8'.split())
    ax.text(C3 + W / 2, 69.4, f'{len(_INV)} models,  8 tasks,  {_cells} conditions',
            ha='center', va='top', fontsize=7.4, color=INK, fontweight='bold')
    ax.text(C3 + W / 2, 66.6, 'task-specific model subsets', ha='center', va='top',
            fontsize=6.1, color=MUTE, style='italic')
    for k, (a, b) in enumerate([('model size', '3.3 – 81 GB'),
                                ('prompt structure', '3 variants'),
                                ('context length', '4k – 128k tokens'),
                                ('quantization', 'q4 / q8 / bf16')]):
        yy = 65.0 - k * 1.9
        ax.text(C3 + 3.0, yy, a, fontsize=6.1, color=MUTE, va='center')
        ax.text(C3 + W - 3.0, yy, b, fontsize=6.1, color=INK, va='center', ha='right')

    card(C3, 32, W, 23, '#fdf6e8', '#e3d3ae')
    title(C3 + W / 2, 53, 'A compact desktop workstation', WARN, 8.2)
    lines(C3 + W / 2, 48.6, ['NVIDIA DGX Spark: compact desktop,',
                             '119 GiB unified memory, so weights',
                             'need not fit a discrete GPU'], 6.3, INK)
    ax.text(C3 + W / 2, 40.0, 'chosen because a laboratory can adopt one',
            ha='center', va='top', fontsize=6.1, color=MUTE, style='italic')
    ax.text(C3 + W / 2, 36.6, 'a second node was added to test scaling',
            ha='center', va='top', fontsize=6.1, color=MUTE, style='italic')

    card(C3, 6, W, 24, '#f7eeee', '#e0c2c3')
    title(C3 + W / 2, 29, 'and a plain-script baseline', BAD, 8.2)
    lines(C3 + W / 2, 24.6, ['the same 40 violations, checked by',
                             '220 lines of regular expressions',
                             'and arithmetic — no model at all'], 6.4, INK)
    ax.text(C3 + W / 2, 11.5, 'so that what the models add\ncan be stated as a difference',
            ha='center', va='center', fontsize=6.1, color=MUTE, style='italic')

    arrow(C1 + W + 0.8, C2 - 1.2, 66)
    arrow(C2 + W + 0.8, C3 - 1.2, 66)
    fig.savefig(OUT / 'figure1_concept.png', bbox_inches='tight', dpi=300)
    plt.close(fig)



# ---------------------------------------------------------------- Figure 2 (tasks)
def fig_tasks():
    """What each of the eight tasks asks a model to do. Design, not results."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    PAGE, RULE, HIT, MISS = '#eef2f5', '#c9d3dc', ACC, BAD
    fig, axes = plt.subplots(2, 4, figsize=(7.4, 3.6))
    for a in axes.ravel():
        a.set_xlim(0, 100); a.set_ylim(0, 100); a.axis('off')

    def page(a, x, y, w, h, fc=PAGE, ec=RULE):
        a.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=1.2',
                                   fc=fc, ec=ec, lw=.7, zorder=2))

    def textlines(a, x, y, w, n, gap=4.0, c='#c2ccd4', lw=1.5, skip=()):
        for k in range(n):
            if k in skip:
                continue
            a.plot([x, x + w * (.62 if k % 3 == 2 else 1)], [y - k * gap] * 2,
                   color=c, lw=lw, solid_capstyle='round', zorder=3)

    def mark(a, x, y, c=MISS, r=2.0):
        a.add_patch(plt.Circle((x, y), r, fc=c, lw=0, zorder=5))

    def arrow(a, x1, y1, x2, y2, c='#9fb0bc'):
        a.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                    mutation_scale=9, color=c, lw=1.0, zorder=4))

    def cap(a, tid, name, sub):
        a.text(0, 99, tid, fontsize=8.6, fontweight='bold', color=ACC, va='top')
        a.text(11, 99, name, fontsize=8.0, color=INK, va='top', fontweight='bold')
        a.text(0, 88, sub, fontsize=6.2, color=MUTE, va='top')

    # ---- T1 compliance: rulebook + manuscript -> marked violations
    a = axes[0][0]; cap(a, 'T1', 'Compliance', 'a manuscript against the rules')
    page(a, 2, 22, 30, 54, '#fdf6e8', '#e3d3ae'); textlines(a, 6, 70, 22, 11, 4.2, '#ddcfae')
    a.text(17, 17, 'guidelines', ha='center', fontsize=6.0, color=MUTE)
    page(a, 46, 22, 30, 54); textlines(a, 50, 70, 22, 11, 4.2)
    for yy in (66, 54, 41, 33):
        mark(a, 78, yy)
    a.text(61, 17, 'manuscript', ha='center', fontsize=6.0, color=MUTE)
    arrow(a, 33, 50, 45, 50)
    a.text(88, 50, '40\nseeded', ha='center', va='center', fontsize=6.4,
           color=MISS, fontweight='bold')

    # ---- T2 review: long paper -> a few points, compared with real reviewers
    a = axes[0][1]; cap(a, 'T2', 'Review support', 'points a reviewer would raise')
    page(a, 2, 14, 26, 62); textlines(a, 5, 71, 19, 14, 4.0)
    a.text(15, 9, '79k tokens', ha='center', fontsize=6.0, color=MUTE)
    arrow(a, 29, 45, 40, 45)
    for k in range(3):
        page(a, 43, 60 - k * 13, 24, 9, 'white')
        a.plot([46, 62], [64.5 - k * 13] * 2, color='#c2ccd4', lw=1.4)
    a.text(55, 74, 'model', ha='center', fontsize=6.2, color=MUTE)
    for k in range(3):
        a.add_patch(plt.Rectangle((74, 58 - k * 13), 22, 9, fc='#eef4f5', ec=ACC,
                                  lw=.7, zorder=2))
    a.text(85, 74, 'real reviewers', ha='center', fontsize=6.2, color=ACC)
    a.text(70, 14, 'model output scored against\n12 points the reviewers made',
           ha='center', va='top', fontsize=6.0, color=MUTE)
    a.plot([68, 72], [64, 64], color=ACC, lw=1.2, ls=':')
    a.plot([68, 72], [51, 51], color=ACC, lw=1.2, ls=':')

    # ---- T3 references: before -> after
    a = axes[0][2]; cap(a, 'T3', 'References / rules', 'convert format, answer queries')
    page(a, 2, 46, 92, 22, 'white')
    a.text(6, 60, 'Harada Y, et al. PNAS 96, 709 (1999)', fontsize=6.0, color=MUTE)
    a.text(6, 52, 'style: wrong journal abbreviation', fontsize=5.6, color=MISS)
    arrow(a, 50, 43, 50, 34)
    page(a, 2, 8, 92, 22, '#eef4f5', ACC)
    a.text(6, 22, 'Harada, Y., et al. Proc. Natl. Acad.', fontsize=6.0, color=INK)
    a.text(6, 14, 'Sci. U.S.A. 96, 709–715 (1999).', fontsize=6.0, color=INK)

    # ---- T4 hallucination: question with no answer
    a = axes[0][3]; cap(a, 'T4', 'Hallucination', 'questions with no answer')
    page(a, 2, 40, 40, 40); textlines(a, 6, 74, 30, 8, 4.2)
    a.text(22, 34, 'source text', ha='center', fontsize=6.0, color=MUTE)
    a.text(52, 70, '"What is the', fontsize=6.4, color=INK)
    a.text(52, 62, 'legend word limit?"', fontsize=6.4, color=INK)
    a.text(52, 50, 'not stated anywhere', fontsize=5.8, color=MISS, style='italic')
    a.add_patch(FancyBboxPatch((52, 22), 44, 18, boxstyle='round,pad=0,rounding_size=1.2',
                               fc='#eef4f5', ec=ACC, lw=.7, zorder=2))
    a.text(74, 31, 'correct answer:\n"not specified"', ha='center', va='center',
           fontsize=6.2, color=ACC, fontweight='bold', zorder=3)

    # ---- T5 figures
    a = axes[1][0]; cap(a, 'T5', 'Figures (vision)', 'defects visible in the image')
    page(a, 2, 24, 44, 52, 'white')
    rng = np.random.default_rng(3)
    xs = np.linspace(10, 40, 14); ys = 36 + 22 * rng.random(14)
    a.plot(xs, ys, color=ACC, lw=1.0)
    a.plot([9, 9], [32, 66], color='#9fb0bc', lw=.8)
    a.plot([9, 42], [32, 32], color='#9fb0bc', lw=.8)
    a.text(24, 27, 'axis labels too small', ha='center', fontsize=4.6, color=MISS)
    mark(a, 41, 68, MISS, 2.4)
    a.text(24, 17, 'image + file metadata', ha='center', va='top',
           fontsize=5.8, color=MUTE)
    a.add_patch(FancyBboxPatch((54, 30), 42, 34, boxstyle='round,pad=0,rounding_size=1.2',
                               fc='#f7eeee', ec='#e0c2c3', lw=.7, zorder=2))
    for k, t in enumerate(['72 dpi', 'panel labels', 'unreadable axes',
                           'table as image', 'vertical rules']):
        a.text(58, 58 - k * 6.4, '• ' + t, fontsize=5.8, color=INK, zorder=3)
    a.text(75, 24, '5 defects, plus one\nfigure with none', ha='center', va='top',
           fontsize=6.0, color=MUTE)

    # ---- T6 self-consistency: two numbers that cannot both hold
    a = axes[1][1]; cap(a, 'T6', 'Self-consistency', 'numbers that contradict')
    # set on two centred lines: a single line of either value ran past the right
    # edge of its box
    page(a, 2, 48, 44, 30); a.text(6, 69, 'Methods', fontsize=6.0, color=MUTE)
    a.text(24, 60, 'runs covered\n200 ns', ha='center', va='center',
           fontsize=6.2, color=INK, linespacing=1.3)
    page(a, 54, 48, 44, 30); a.text(58, 69, 'Results', fontsize=6.0, color=MUTE)
    a.text(76, 60, 'saturates at\n' + r'400 $\mathregular{s^{-1}}$', ha='center',
           va='center', fontsize=6.2, color=INK, linespacing=1.3)
    arrow(a, 24, 45, 42, 33); arrow(a, 76, 45, 58, 33)
    # widened from x=22 w=56: 'period 2.5 ms = 2,500,000 ns' overflowed both edges
    a.add_patch(FancyBboxPatch((6, 10), 88, 21, boxstyle='round,pad=0,rounding_size=1.2',
                               fc='#f7eeee', ec='#e0c2c3', lw=.7, zorder=2))
    a.text(50, 24, 'period 2.5 ms = 2,500,000 ns', ha='center', fontsize=6.0,
           color=INK, zorder=3)
    a.text(50, 15, 'off by 4 orders of magnitude', ha='center', fontsize=6.4,
           color=MISS, fontweight='bold', zorder=3)

    # ---- T7 category-conditional rules
    a = axes[1][2]; cap(a, 'T7', 'Category rules', 'which rules even apply')
    a.add_patch(FancyBboxPatch((2, 62), 40, 16, boxstyle='round,pad=0,rounding_size=1.2',
                               fc='#fdf6e8', ec='#e3d3ae', lw=.7, zorder=2))
    a.text(22, 70, 'submitted as\na Commentary', ha='center', va='center',
           fontsize=6.2, color=INK, zorder=3)
    arrow(a, 44, 70, 54, 70)
    for k, (t, c, lab) in enumerate([('5 rules', '#dfe5ea', 'exempt'),
                                     ('8 rules', ACC, 'still apply')]):
        a.add_patch(plt.Rectangle((57, 66 - k * 15), 20, 11,
                                  fc=c, lw=0, zorder=3))
        a.text(67, 71.5 - k * 15, t, ha='center', va='center', fontsize=6.2,
               color=INK if k == 0 else 'white', fontweight='bold', zorder=4)
        a.text(80, 71.5 - k * 15, lab, va='center', fontsize=6.0,
               color=MUTE if k == 0 else ACC, zorder=4)
    a.text(50, 36, 'flagging an exempt rule', ha='center',
           fontsize=6.8, color=MISS, fontweight='bold')
    a.text(50, 24, 'the failure an editorial office\nactually worries about',
           ha='center', va='top', fontsize=6.0, color=MUTE)

    # ---- T8 tool use
    a = axes[1][3]; cap(a, 'T8', 'Tool use', 'check against a live database')
    page(a, 2, 56, 38, 22, 'white')
    a.text(6, 68, 'reference [7]', fontsize=6.2, color=INK)
    a.text(6, 60, 'DOI 10.1234/…', fontsize=5.8, color=MUTE)
    arrow(a, 42, 66, 54, 66)
    a.add_patch(FancyBboxPatch((56, 54), 42, 24, boxstyle='round,pad=0,rounding_size=1.2',
                               fc='#eef4f5', ec=ACC, lw=.7, zorder=2))
    a.text(77, 70, 'Crossref / NLM', ha='center', fontsize=6.4, color=ACC,
           fontweight='bold', zorder=3)
    a.text(77, 61, 'live API call', ha='center', fontsize=5.8, color=MUTE, zorder=3)
    arrow(a, 77, 51, 77, 42)
    a.text(50, 32, 'resolve, correct the abbreviation,', ha='center', fontsize=6.2,
           color=INK)
    a.text(50, 23, 'and refuse to invent a record', ha='center', fontsize=6.2,
           color=INK)
    a.text(50, 10, 'one DOI in the set does not resolve', ha='center', fontsize=5.8,
           color=MISS, style='italic')

    fig.subplots_adjust(hspace=.34, wspace=.14, left=.012, right=.988,
                        top=.955, bottom=.015)
    fig.savefig(OUT / 'figure2_tasks.png', bbox_inches='tight', dpi=300)
    plt.close(fig)



# ---------------------------------------------------- Figure 6 (prompt structure)
def n_up_pre(pairs):
    return sum(1 for v in pairs.values() if v['b'] >= v['a'])


def fig_prompt():
    """What changes the score: prompt structure against the things a purchase buys."""
    import csv as _csv
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9),
                             gridspec_kw={'width_ratios': [1.05, 1.0, 1.55]})

    # ---- A: every model improves from free-form to checklist
    # Pair the two prompt forms at the same reasoning effort. Pooling over effort
    # compared gpt-oss:120b's best free-form run (medium effort, 16) against its only
    # checklist run (low effort, 0), which overstates the drop; at matched effort it
    # is 11 to 0. The counts are the same either way.
    best = {}
    for r in rows('t1'):
        if r.get('manuscript') != 'MS-A':
            continue
        v = (r.get('variant') or 'a').lower()
        if v not in ('a', 'b'):
            continue
        key = (r['model'], (r.get('think') or '').strip() or '-')
        try:
            d = float(r['detected'])
        except Exception:
            continue
        best.setdefault(key, {})
        best[key][v] = max(best[key].get(v, 0), d)
    pairs = {k: v for k, v in best.items() if 'a' in v and 'b' in v}
    ax = axes[0]
    for m, v in pairs.items():
        up = v['b'] >= v['a']   # ties drawn as raises; the title counts them apart
        ax.plot([0, 1], [v['a'], v['b']], '-o', ms=3.4, lw=1.1,
                color=ACC if up else BAD, alpha=.85,
                zorder=3 if up else 4)
    ax.set_xlim(-.35, 1.35); ax.set_xticks([0, 1])
    ax.set_xticklabels(['free-form', 'checklist'], fontsize=7.5)
    ax.set_ylabel('violations detected (of 40)')
    _up = sum(1 for v in pairs.values() if v['b'] > v['a'])
    _dn = sum(1 for v in pairs.values() if v['b'] < v['a'])
    _eq = len(pairs) - _up - _dn
    ax.set_title(f'Structure raises {_up} of {len(pairs)} models, lowers {_dn},\n'
                 f'and leaves {_eq} detecting nothing either way',
                 fontsize=8, pad=4)
    ax.grid(axis='y', alpha=.18, lw=.4)
    ax.text(.5, .90, 'red: those it lowers', transform=ax.transAxes,
            ha='center', fontsize=6.4, color=BAD)
    # three models score 0 under both forms, so their lines coincide exactly and
    # the panel shows 12 traces for 14 models unless the overlap is named
    _flat = sum(1 for v in pairs.values() if v['a'] == 0 and v['b'] == 0)
    if _flat:
        ax.set_ylim(-3.6, None)
        ax.text(.5, -1.4, f'{_flat} models overlap on this line', va='top',
                ha='center', fontsize=6.2, color=MUTE)

    # ---- B: how the shift splits by difficulty class for one model
    diff = json.loads((ROOT / 'data/groundtruth/MS-A_difficulty.json').read_text())
    HARD, EASY = set(diff['hard']), set(diff['easy'])

    def split(model, variant):
        for r in rows('t1'):
            if (r.get('model') == model and r.get('manuscript') == 'MS-A'
                    and (r.get('variant') or 'a') == variant):
                missed = {x for x in (r.get('missed_ids') or '').split(',') if x}
                return len(EASY - missed), len(HARD - missed)
        return None

    cmp_spec = json.loads((ROOT / 'data/score_change_comparisons.json').read_text())
    ref = next(c for c in cmp_spec['comparisons'] if 'checklist' in c['label'])
    a_split, b_split = split(**{'model': ref['from']['model'], 'variant': ref['from']['variant']}), \
                       split(**{'model': ref['to']['model'], 'variant': ref['to']['variant']})
    ax = axes[1]
    x = np.arange(2)
    easy = [a_split[0], b_split[0]]
    hard = [a_split[1], b_split[1]]
    ax.bar(x - .18, easy, .34, color='#cfd9e0', label=f'EASY ({len(EASY)})')
    ax.bar(x + .18, hard, .34, color=ACC, label=f'HARD ({len(HARD)})')
    for xi, (e, h) in enumerate(zip(easy, hard)):
        ax.text(xi - .18, e + .5, str(e), ha='center', fontsize=7, color=INK)
        ax.text(xi + .18, h + .5, str(h), ha='center', fontsize=7,
                color=ACC, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(['free-form', 'checklist'], fontsize=7)
    ax.set_xlim(-.62, 1.62)
    ax.set_ylim(0, max(easy + hard) + 6); ax.set_ylabel('detected')
    ax.set_title(f'split by difficulty class\n{short(ref["from"]["model"])}', fontsize=8, pad=4)
    ax.legend(frameon=False, fontsize=6.4, loc='upper left')
    ax.grid(axis='y', alpha=.18, lw=.4)

    # ---- C: each change, scored from the data rather than typed in
    def detected(model, variant):
        for r in rows('t1'):
            if (r.get('model') == model and r.get('manuscript') == 'MS-A'
                    and (r.get('variant') or 'a') == variant):
                return float(r['detected'])
        raise KeyError(f'{model} variant {variant} not in results')

    def _pair_note(c):
        """Name the models a comparison is between, taken from the comparison file
        rather than typed here, so the label cannot drift from what was measured."""
        if c.get('effect_from') == 'deterministic_baseline':
            return 'no model'
        a, b = c['from']['model'], c['to']['model']
        return short(a) if a == b else f'{short(a)} to {short(b)}'

    items = []
    for c in cmp_spec['comparisons']:
        if c.get('effect_from') == 'deterministic_baseline':
            eff = DETERMINISTIC_BASELINE
        else:
            eff = detected(**c['to']) - detected(**c['from'])
        col = ACC if eff > 1 else (WARN if eff > 0 else BAD)
        items.append((c['label'], c['memory_delta_gib'], eff, col, _pair_note(c)))
    ax = axes[2]
    y = np.arange(len(items))[::-1]
    ax.barh(y, [i[2] for i in items], .5, color=[i[3] for i in items])
    # negative bars grow leftward, so their value label must sit to the right of
    # zero or it lands on the category name and is clipped
    for yi, (lab, mem, eff, c, _n) in zip(y, items):
        note = '±0 GiB' if mem == 0 else f'{mem:+.1f} GiB'
        x0 = max(eff, 0)
        ax.text(x0 + 1.2, yi, f'{eff:+g}', va='center', ha='left',
                fontsize=7.4, color=c, fontweight='bold')
        ax.text(x0 + 9.0, yi, note, va='center', ha='left',
                fontsize=6.3, color=MUTE)
    # each row names the models it compares, on a second line under the change
    ax.set_yticks(y); ax.set_yticklabels([])
    _tr = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for yi, it in zip(y, items):
        ax.text(-.02, yi + .21, it[0], transform=_tr, ha='right', va='center',
                fontsize=6.8, color=INK)
        ax.text(-.02, yi - .23, it[4], transform=_tr, ha='right', va='center',
                fontsize=5.7, color=MUTE)
    ax.set_xlim(-9, 58)
    ax.set_xlabel('change in violations detected')
    ax.axvline(0, color=INK, lw=.7)
    ax.set_title('Observed score difference per comparison,\nand its cost in memory',
                 fontsize=8, pad=4)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='x', alpha=.18, lw=.4)

    fig.tight_layout()
    fig.savefig(OUT / 'figure6_prompt_structure.png', bbox_inches='tight', dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2
def fig2():
    fig, axes = plt.subplots(2, 5, figsize=(7.2, 3.6), sharey=True)
    for ax, (label, *_rest) in zip(axes.ravel(), TASKS):
        d = SCORES[label]
        xs = [SIZE[m] for m in d if m in SIZE]
        ys = [d[m][1] for m in d if m in SIZE]
        ax.scatter(xs, ys, s=16, color=ACC, alpha=.85, zorder=3, linewidths=0)
        if len(xs) > 2:
            rs = spearman(xs, ys)
            ax.text(.04, .06, f'$r_s$ = {rs:+.2f}\nn = {len(xs)}', transform=ax.transAxes,
                    fontsize=6.5, color=MUTE, va='bottom')
        ax.set_xscale('log'); ax.set_title(label, fontsize=7.5, pad=3)
        ax.set_xticks([10, 100]); ax.set_xticklabels(['10', '100'])
        ax.set_ylim(-.06, 1.12); ax.grid(alpha=.18, lw=.4)
        if label == 'T1 guidelines':
            for a, b, c in [('gpt-oss:20b', 'gpt-oss:120b', BAD),
                            ('qwen3.6:35b-a3b-q4_K_M', 'qwen3.8:27b', ACC)]:
                if a in d and b in d:
                    ax.annotate('', xy=(SIZE[b], d[b][1]), xytext=(SIZE[a], d[a][1]),
                                arrowprops=dict(arrowstyle='->', lw=1.1, color=c,
                                                shrinkA=3, shrinkB=3))
            # the in-panel caption sat on top of the r_s text and the data, and named
            # only one of the two arrows; the legend names both instead
    for ax in axes[:, 0]:
        ax.set_ylabel('normalised score')
    for ax in axes[1]:
        ax.set_xlabel('model weights (GB)')
    fig.suptitle('No consistent monotonic ordering by model size '
                 '(Spearman rank correlation, best configuration per model)',
                 fontsize=9, y=1.0)
    fig.tight_layout(); fig.savefig(OUT / 'figure4_size_vs_score.png', bbox_inches='tight'); plt.close(fig)

    # The manuscript quotes a bound on these coefficients and the range they span.
    # Writing them out here makes the figure the single place they are computed, so
    # check_claims.py can compare the text against the same numbers the panels show
    # instead of recomputing them from a second implementation.
    stats = {}
    for label, *_rest in TASKS:
        d = SCORES[label]
        xs = [SIZE[m] for m in d if m in SIZE]
        ys = [d[m][1] for m in d if m in SIZE]
        if len(xs) > 2:
            stats[label] = {'spearman': round(spearman(xs, ys), 4), 'n': len(xs)}
    (ROOT / 'results' / 'derived_stats.json').write_text(
        json.dumps({'note': 'written by harness/make_paper_figures.py; do not edit',
                    'size_vs_score': stats}, indent=1) + '\n')
    rr = [v['spearman'] for v in stats.values()]
    print(f'  derived_stats.json  spearman {min(rr):+.2f} to {max(rr):+.2f}, '
          f'max |r| {max(abs(x) for x in rr):.2f}')


# ---------------------------------------------------------------- Figure 2b
def fig2b():
    labels = [t[0] for t in TASKS]
    ranked = {}
    for lb in labels:
        d = SCORES[lb]
        order = sorted(d, key=lambda m: -d[m][1])
        ranked[lb] = {m: i + 1 for i, m in enumerate(order)}
    HI = {'gpt-oss:20b': BAD, 'qwen3.8:27b': ACC, 'qwen3.5:122b-a10b-q4_K_M': WARN}
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    allm = sorted({m for lb in labels for m in ranked[lb]})
    for m in allm:
        # NaN at a task the model cannot do, so the line breaks instead of
        # implying a value across the gap (e.g. a text-only model has no T5).
        xs = list(range(len(labels)))
        ys = [ranked[lb].get(m, np.nan) for lb in labels]
        if sum(not np.isnan(v) for v in ys) < 2:
            continue
        c = HI.get(m, '#d7dde2')
        ax.plot(xs, ys, '-o', color=c, lw=2.0 if m in HI else .7,
                ms=4 if m in HI else 2.4, zorder=3 if m in HI else 1,
                alpha=1 if m in HI else .8)
        # Every line is named at its first measured task rather than only the
        # three highlighted ones. All 17 lines begin at T1, where the ranks are
        # 1..17 and therefore distinct, so the labels cannot collide. The grey
        # lines are too light to read as text, so their labels take MUTE.
        first = min(i for i, v in enumerate(ys) if not np.isnan(v))
        ax.annotate(short(m), xy=(first, ys[first]), xytext=(-7, 0),
                    textcoords='offset points', fontsize=6.6, va='center',
                    ha='right', color=c if m in HI else '#7d8b98',
                    fontweight='bold' if m in HI else 'normal')
    ax.invert_yaxis()
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=7)
    # the rank numbers move to the right edge: the left margin now carries a model
    # name at every rank, and the two collided there
    ax.yaxis.tick_right(); ax.yaxis.set_label_position('right')
    ax.spines['right'].set_visible(True); ax.spines['left'].set_visible(False)
    ax.set_ylabel('rank within task (1 = best)')
    ax.set_title('No model led across all measured tasks', fontsize=9)
    ax.grid(axis='y', alpha=.18, lw=.4)
    fig.tight_layout(); fig.savefig(OUT / 'figure5_rank_inversion.png', bbox_inches='tight'); plt.close(fig)


# ---------------------------------------------------------------- Figure 3
def fig3():
    want = [('t1', 'qwen3.8:27b', 'T1 guidelines'), ('t1', 'qwen3.6:35b-a3b-q8_0', 'T1 guidelines'),
            ('t1', 'gpt-oss:120b', 'T1 guidelines'),
            ('t2', 'qwen3.8:27b', 'T2 review'), ('t2', 'gpt-oss:20b', 'T2 review'),
            ('t2', 'gpt-oss:120b', 'T2 review')]
    bars = []
    for task, model, tl in want:
        cand = []
        for f in glob.glob(str(ROOT / 'results' / task / '*.json')):
            try:
                d = json.load(open(f))
            except Exception:
                continue
            mt = d.get('meta') or {}
            if d.get('model') != model or not mt.get('output_tokens'):
                continue
            if task == 't1':
                # the recommended operating point is variant B on MS-A; picking by
                # longest decode would silently select variant A and disagree with
                # the numbers quoted in the text.
                if 'MS-A' not in f or 'variant-b' not in f:
                    continue
            if not mt.get('prefill_tok_s') or not mt.get('decode_tok_s'):
                continue
            cand.append((mt['prompt_tokens'] / mt['prefill_tok_s'],
                         mt['output_tokens'] / mt['decode_tok_s'], mt))
        if cand:
            pf, dc, mt = cand[0] if task == 't1' else max(cand, key=lambda c: c[1])
            bars.append((f'{tl}\n{short(model)}', pf, dc, mt))
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    y = np.arange(len(bars))
    pf = [b[1] for b in bars]; dc = [b[2] for b in bars]
    ax.barh(y, pf, color=ACC, height=.55, label='prefill (reading)')
    ax.barh(y, dc, left=pf, color=WARN, height=.55, label='decode (writing)')
    for i, (lb, p, d, mt) in enumerate(bars):
        tot = p + d
        ax.text(tot + max(pf + dc) * .02, i, f'{d/tot*100:.0f}% decode',
                va='center', fontsize=6.5, color=INK)
        ax.text(tot * .5, i - .38, f'in {mt["prompt_tokens"]:,} / out {mt["output_tokens"]:,} tok',
                va='center', ha='center', fontsize=6, color=MUTE)
    ax.set_yticks(y); ax.set_yticklabels([b[0] for b in bars], fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel('wall-clock seconds')
    ax.legend(frameon=False, fontsize=7, loc='lower right')
    ax.set_title('The long-input review task shifts wall time toward prefill', fontsize=9)
    ax.grid(axis='x', alpha=.18, lw=.4)
    fig.tight_layout(); fig.savefig(OUT / 'figure7_prefill_decode.png', bbox_inches='tight'); plt.close(fig)


# ---------------------------------------------------------------- Figure 4
def fig4():
    rws = json.loads((ROOT / 'results' / 'twonode' / 'matrix.json').read_text())
    # Both measured models are plotted. Colour carries the configuration and marker
    # shape carries the model, so the two are read independently; the smaller model
    # was measured over three prompt lengths and on RDMA only.
    agg = collections.defaultdict(list)
    sizes = {}
    for r in rws:
        if r['metric'] != 'prefill':
            continue
        agg[(r['model'], r['nodes'], r['prompt'])].append(r['tok_s'])
        sizes[r['model']] = r['size_gib']
    models = sorted(sizes, key=lambda m: -sizes[m])
    marks = ['o', '^']
    series = [('ONE', '1 node', INK, '-'), ('TWO', '2 nodes, RoCE/RDMA', ACC, '-'),
              ('TWO-TCP', '2 nodes, TCP', BAD, '--')]
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for mi, mdl in enumerate(models):
        for key, lab, c, st in series:
            pts = sorted((p, np.mean(v)) for (m, n, p), v in agg.items()
                         if m == mdl and n == key)
            if pts:
                ax.plot([p for p, _ in pts], [v for _, v in pts], st, color=c,
                        marker=marks[mi], lw=1.4, ms=4,
                        mfc=c if mi == 0 else 'white', mew=1.0)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('prompt length (tokens)'); ax.set_ylabel('prefill throughput (tok/s)')
    ax.set_title('Two nodes improve prefill over RDMA but not TCP', fontsize=9)
    cfg = [Line2D([], [], color=c, ls=st, lw=1.4, label=lab) for _, lab, c, st in series]
    mdl_h = [Line2D([], [], color=MUTE, ls='none', marker=marks[i], ms=4,
                    mfc=MUTE if i == 0 else 'white', mew=1.0,
                    label=f'{sizes[m]:.2f} GiB model')
             for i, m in enumerate(models)]
    lg = ax.legend(handles=cfg, frameon=False, fontsize=7, loc='lower left')
    ax.add_artist(lg)
    ax.legend(handles=mdl_h, frameon=False, fontsize=7, loc='upper right')
    ax.grid(alpha=.18, lw=.4, which='both')
    for mi, mdl in enumerate(models):
        one = {p: np.mean(v) for (m, n, p), v in agg.items() if m == mdl and n == 'ONE'}
        two = {p: np.mean(v) for (m, n, p), v in agg.items() if m == mdl and n == 'TWO'}
        for p in sorted(set(one) & set(two)):
            ax.annotate(f'{two[p]/one[p]:.2f}×', xy=(p, two[p]),
                        xytext=(0, -11 if mi == 0 else 6),
                        textcoords='offset points', fontsize=6, color=ACC, ha='center')
    ax.set_xlim(3300, 1.7e5)   # room for the leftmost ratio labels
    ax.axvline(71230, color=MUTE, lw=.6, ls=':')
    ax.text(71230, ax.get_ylim()[0] * 1.2, ' one paper', fontsize=6, color=MUTE)
    fig.tight_layout(); fig.savefig(OUT / 'figure8_twonode.png', bbox_inches='tight'); plt.close(fig)


for fn in (fig_graphical_abstract, fig_concept, fig_tasks, fig2, fig2b, fig_prompt, fig3, fig4):
    fn(); print('ok', fn.__name__)
for p in sorted(OUT.glob('*.png')):
    print(f'  {p.name}  {p.stat().st_size/1024:.0f} KB')


def fig_tiles():
    """Per-violation detection: the checker and every model condition against all 40 items.

    Drawn because the aggregate counts (31, 34, 40) hide which items each layer
    reaches, and the complementarity claim is about the pattern, not the totals.
    Detection is read from missed_ids in results/t1_summary.csv; the checker's row
    is read from harness/deterministic_check.py, not typed in.
    """
    import subprocess, re as _re
    out = subprocess.run(['python3', str(ROOT / 'harness/deterministic_check.py')],
                         capture_output=True, text=True).stdout
    tail = out.split('判定不能')[-1]
    unreachable = set(_re.findall(r'\bV\d{2}\b', tail))
    all_ids = sorted(set(_re.findall(r'\bV\d{2}\b', out)))
    if not all_ids:
        print('fig_tiles: no items parsed from the checker; skipped')
        return
    checker = [i not in unreachable for i in all_ids]

    rows = [r for r in csv.DictReader((ROOT / 'results/t1_summary.csv').open())
            if r['manuscript'] == 'MS-A']
    # several conditions share a model and variant (repeat seeds, reasoning-effort
    # sweep); label them apart or the plot shows five identical rows
    base = collections.Counter(f"{short(r['model'])} ({r.get('variant') or 'a'})" for r in rows)
    conds = []
    for r in rows:
        missed = {x for x in (r.get('missed_ids') or '').split(',') if x}
        lab = f"{short(r['model'])} ({r.get('variant') or 'a'})"
        if base[lab] > 1:
            extra = [f"s{r['seed']}"] if r.get('seed') not in (None, '', '42') else []
            if r.get('think') not in (None, '', 'None'):
                extra.append(r['think'])
            if extra:
                lab += ' ' + ','.join(extra)
        conds.append((lab, [i not in missed for i in all_ids],
                      sum(i not in missed for i in all_ids)))
    conds.sort(key=lambda c: -c[2])

    labels = ['deterministic checker'] + [c[0] for c in conds]
    grid = np.array([checker] + [c[1] for c in conds], dtype=float)

    h = 0.9 + 0.16 * len(labels)
    fig, ax = plt.subplots(figsize=(7.2, h))
    ax.imshow(grid, cmap=matplotlib.colors.ListedColormap(['#eef1f4', ACC]),
              aspect='auto', vmin=0, vmax=1, interpolation='nearest')
    ax.set_xticks(range(len(all_ids)))
    ax.set_xticklabels(all_ids, rotation=90, fontsize=5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=5.5)
    ax.get_yticklabels()[0].set_fontweight('bold')
    ax.set_xticks(np.arange(-.5, len(all_ids), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(labels), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=.6)
    ax.tick_params(which='minor', length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.axhline(.5, color=INK, lw=.9)
    ax.set_xlabel('seeded violation', fontsize=7)
    never = [all_ids[j] for j in range(len(all_ids)) if not any(c[1][j] for c in conds)]
    n_never = len(never)
    # Columns are marked by a symbol prefixed to the tick label, not by colour, so the
    # distinction survives greyscale printing and colour-blind readers. Detection
    # itself is the only thing colour encodes, and the key shows it as a swatch.
    ax.set_xticklabels([('* ' if i in never else '\u2020 ' if i in unreachable else '')
                        + i for i in all_ids], rotation=90, fontsize=5)
    key = [Patch(fc=ACC, ec='none', label='detected'),
           Patch(fc='#eef1f4', ec='none', label='not detected')]
    ax.legend(handles=key, loc='lower left', bbox_to_anchor=(0, 1.005), ncol=2,
              frameon=False, fontsize=6, handlelength=1.1, handleheight=1.0,
              columnspacing=1.2, handletextpad=.5)
    ax.set_title('\u2020 the checker cannot decide these in code    '
                 '* found by no model condition',
                 fontsize=6, loc='right', pad=4, color=MUTE)
    fig.tight_layout()
    fig.savefig(OUT / 'figure3_detection_tiles.png', dpi=300)
    plt.close(fig)
    print(f'figure3_detection_tiles.png  {len(labels)} rows x {len(all_ids)} items; '
          f'checker {sum(checker)}/{len(all_ids)}; found by no model: {never or "none"}')


fig_tiles()
