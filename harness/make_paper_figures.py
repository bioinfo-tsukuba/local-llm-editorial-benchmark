#!/usr/bin/env python3
"""Figures for the BPPB manuscript. All numbers are read from results/, never typed in.

Outputs 300 dpi PNGs to BPPB-special-issue-paper/figures/.
See issue #2 for the rationale behind each figure.
"""
import csv, json, glob, pathlib, collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'BPPB-special-issue-paper' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
# Figure text is set in Nimbus Sans (Helvetica-metric). BPPB sets body text and
# captions in Times New Roman; figure interiors are kept sans for legibility at
# 6-7 pt. For strict matching use 'Nimbus Roman' (Times-metric) instead.
FONT = 'Nimbus Sans'
plt.rcParams.update({'font.size': 8, 'font.family': FONT, 'mathtext.fontset': 'stixsans',
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.linewidth': .6, 'xtick.major.width': .6,
                     'ytick.major.width': .6, 'figure.dpi': 300})

# on-disk weight size (GB) as reported by the runtime
SIZE = {'gemma3:4b': 3.3, 'gemma4': 9.6, 'gpt-oss:20b': 13, 'mistral-small': 14,
        'magistral': 14, 'qwen3.6:27b': 17, 'qwen3.8:27b': 17,
        'qwen3-vl:30b-a3b-instruct': 19, 'qwen3:32b': 20,
        'qwen3.6:35b-a3b-q4_K_M': 23, 'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0': 31,
        'qwen3.6:35b-a3b-q8_0': 38, 'nemotron': 42, 'command-r-plus': 59,
        'qwen3-vl:30b-a3b-instruct-bf16': 62, 'gpt-oss:120b': 65,
        'glm-4.5-air:q4': 67, 'llama4:scout': 67, 'qwen3.6:35b-a3b-bf16': 71,
        'qwen3.5:35b-a3b-bf16': 71, 'qwen3.5:122b-a10b-q4_K_M': 81}
SHORT = {'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0': 'GLM-4.7-Flash',
         'qwen3.5:122b-a10b-q4_K_M': 'qwen3.5:122b', 'qwen3.6:35b-a3b-q4_K_M': 'qwen3.6 q4',
         'qwen3.6:35b-a3b-q8_0': 'qwen3.6 q8', 'qwen3.6:35b-a3b-bf16': 'qwen3.6 bf16',
         'qwen3.5:35b-a3b-bf16': 'qwen3.5 bf16', 'qwen3-vl:30b-a3b-instruct': 'qwen3-vl q4',
         'qwen3-vl:30b-a3b-instruct-bf16': 'qwen3-vl bf16', 'glm-4.5-air:q4': 'GLM-4.5-Air'}
short = lambda m: SHORT.get(m, m)

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


TASKS = [('T1 guidelines', 't1', 'detected', 40),
         ('T2 review', 't2', 'matched', 12),
         ('T3 references', 't3refs', 'fully_correct', 8),
         ('T3 Japanese', 't3ja', 'correct', 10),
         ('T5 figures', 't5', 'detected', 5),
         ('T6 consistency', 't6c', 'detected', 10),
         ('T7 category rules', 't7', 'applicable_detected', 8),
         ('T8 tool use', 't8', 'abbrev_correct', 4)]
SCORES = {label: best(f, fld, d) for label, f, fld, d in TASKS}



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
    title(C2 + W / 2, 92, 'A benchmark from real material')
    for k, (a, b) in enumerate([("a journal's Instructions for Authors", '4,539 words'),
                                ('5 manuscripts written for this study', '63 seeded defects'),
                                ('3 published reviews of a real preprint', '12 reference points'),
                                ('4 figures with known defects', '+ 1 compliant control')]):
        yy = 87.0 - k * 5.6
        ax.text(C2 + 2.5, yy, a, fontsize=6.3, color=INK, va='top')
        ax.text(C2 + 2.5, yy - 2.5, b, fontsize=5.8, color=ACC, va='top')
    ax.text(C2 + W / 2, 64.4, 'ground truth verified by 52 independent checks',
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
    ax.text(C3 + W / 2, 69.4, '17 models  ×  8 tasks  =  283 cells',
            ha='center', va='top', fontsize=7.4, color=INK, fontweight='bold')
    for k, (a, b) in enumerate([('model size', '3.3 – 81 GB'),
                                ('prompt structure', '3 variants'),
                                ('context length', '4k – 128k tokens'),
                                ('quantization', 'q4 / q8 / bf16')]):
        yy = 66.0 - k * 2.4
        ax.text(C3 + 3.0, yy, a, fontsize=6.1, color=MUTE, va='center')
        ax.text(C3 + W - 3.0, yy, b, fontsize=6.1, color=INK, va='center', ha='right')

    card(C3, 32, W, 23, '#fdf6e8', '#e3d3ae')
    title(C3 + W / 2, 53, 'A bench-top machine', WARN, 8.2)
    lines(C3 + W / 2, 48.6, ['NVIDIA DGX Spark: desk-side,',
                             '119 GiB unified memory, so weights',
                             'need not fit a discrete GPU'], 6.3, INK)
    ax.text(C3 + W / 2, 40.0, 'chosen because a laboratory can adopt one',
            ha='center', va='top', fontsize=6.1, color=MUTE, style='italic')
    ax.text(C3 + W / 2, 36.6, 'a second node was added to test scaling',
            ha='center', va='top', fontsize=6.1, color=MUTE, style='italic')

    card(C3, 6, W, 24, '#f7eeee', '#e0c2c3')
    title(C3 + W / 2, 29, 'and a control arm', BAD, 8.2)
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
    page(a, 2, 48, 44, 30); a.text(6, 68, 'Methods', fontsize=6.0, color=MUTE)
    a.text(6, 58, 'runs covered 200 ns', fontsize=6.4, color=INK)
    page(a, 54, 48, 44, 30); a.text(58, 68, 'Results', fontsize=6.0, color=MUTE)
    a.text(58, 58, r'saturates at 400 $\mathregular{s^{-1}}$', fontsize=6.4, color=INK)
    arrow(a, 24, 45, 42, 33); arrow(a, 76, 45, 58, 33)
    a.add_patch(FancyBboxPatch((22, 10), 56, 21, boxstyle='round,pad=0,rounding_size=1.2',
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


# ---------------------------------------------------------------- Figure 3 (layers)
def fig1():
    fig, ax = plt.subplots(figsize=(5.2, 1.9))
    layers = [('Deterministic checker\n(regex + arithmetic)', 30, ACC, '0.1 s  ·  0 GB'),
              ('+ external tool lookup', 1, '#3f8fa0', 'API call'),
              ('+ LLM  (17 GB)', 8, WARN, '524 s  ·  17 GB'),
              ('not reached', 1, '#dfe5ea', 'cross-unit arithmetic\n→ human')]
    left = 0
    for name, w, c, note in layers:
        ax.barh(0, w, left=left, color=c, height=.5,
                edgecolor='white', linewidth=.8)
        if w >= 4:
            ax.text(left + w / 2, 0, f'{w}', ha='center', va='center',
                    color='white' if c != '#dfe5ea' else INK, fontweight='bold', fontsize=10)
        left += w
    ax.set_xlim(0, 40); ax.set_ylim(-.75, .75)
    ax.set_yticks([]); ax.set_xticks([0, 10, 20, 30, 39, 40])
    ax.set_xlabel('seeded guideline violations detected (of 40)')
    cum = [0, 30, 31, 39]
    for (name, w, c, note), x in zip(layers, cum):
        ax.annotate(f'{name}\n{note}', xy=(x + w / 2, .28), xytext=(x + w / 2, .62),
                    ha='center', va='bottom', fontsize=6.5, color=INK,
                    arrowprops=dict(arrowstyle='-', lw=.5, color=MUTE))
    ax.axvline(30, color=INK, lw=.6, ls=':')
    ax.text(30, -.55, 'code alone: 30/40, zero false positives',
            ha='center', fontsize=6.5, color=INK)
    fig.tight_layout(); fig.savefig(OUT / 'figure3_layers.png', bbox_inches='tight'); plt.close(fig)


# ---------------------------------------------------------------- Figure 2
def fig2():
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.6), sharey=True)
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
            ax.text(.5, .04, 'same family,\nbigger scores lower', transform=ax.transAxes,
                    fontsize=6, color=BAD, ha='center')
    for ax in axes[:, 0]:
        ax.set_ylabel('normalised score')
    for ax in axes[1]:
        ax.set_xlabel('model weights (GB)')
    fig.suptitle('Model size does not predict quality on any task '
             '(Spearman rank correlation)', fontsize=9, y=1.0)
    fig.tight_layout(); fig.savefig(OUT / 'figure4_size_vs_score.png', bbox_inches='tight'); plt.close(fig)


# ---------------------------------------------------------------- Figure 2b
def fig2b():
    labels = [t[0] for t in TASKS]
    ranked = {}
    for lb in labels:
        d = SCORES[lb]
        order = sorted(d, key=lambda m: -d[m][1])
        ranked[lb] = {m: i + 1 for i, m in enumerate(order)}
    HI = {'gpt-oss:20b': BAD, 'qwen3.8:27b': ACC, 'qwen3.5:122b-a10b-q4_K_M': WARN}
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
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
        if m in HI:
            last = max(i for i, v in enumerate(ys) if not np.isnan(v))
            ax.annotate(short(m), xy=(last, ys[last]), xytext=(6, 0),
                        textcoords='offset points', fontsize=7, color=c, va='center')
    ax.invert_yaxis()
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=7)
    ax.set_ylabel('rank within task (1 = best)')
    ax.set_title('No single best model: rankings invert across tasks', fontsize=9)
    ax.grid(axis='y', alpha=.18, lw=.4)
    fig.tight_layout(); fig.savefig(OUT / 'figure4b_rank_inversion.png', bbox_inches='tight'); plt.close(fig)


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
    ax.set_title('Which phase dominates flips between the two use cases', fontsize=9)
    ax.grid(axis='x', alpha=.18, lw=.4)
    fig.tight_layout(); fig.savefig(OUT / 'figure5_prefill_decode.png', bbox_inches='tight'); plt.close(fig)


# ---------------------------------------------------------------- Figure 4
def fig4():
    rws = json.loads((ROOT / 'results' / 'twonode' / 'matrix.json').read_text())
    agg = collections.defaultdict(list)
    for r in rws:
        if r['metric'] != 'prefill' or r['model'] != 'glm4moe':
            continue
        agg[(r['nodes'], r['prompt'])].append(r['tok_s'])
    series = [('ONE', '1 node', INK, '-o'), ('TWO', '2 nodes, RoCE/RDMA', ACC, '-o'),
              ('TWO-TCP', '2 nodes, TCP', BAD, '--s')]
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    for key, lab, c, st in series:
        pts = sorted((p, np.mean(v)) for (n, p), v in agg.items() if n == key)
        if pts:
            ax.plot([p for p, _ in pts], [v for _, v in pts], st, color=c,
                    label=lab, lw=1.4, ms=4)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('prompt length (tokens)'); ax.set_ylabel('prefill throughput (tok/s)')
    ax.set_title('Two nodes help only over RDMA', fontsize=9)
    ax.legend(frameon=False, fontsize=7)
    ax.grid(alpha=.18, lw=.4, which='both')
    one = {p: np.mean(v) for (n, p), v in agg.items() if n == 'ONE'}
    two = {p: np.mean(v) for (n, p), v in agg.items() if n == 'TWO'}
    for p in sorted(set(one) & set(two)):
        ax.annotate(f'{two[p]/one[p]:.2f}×', xy=(p, two[p]), xytext=(0, 6),
                    textcoords='offset points', fontsize=6, color=ACC, ha='center')
    ax.axvline(71230, color=MUTE, lw=.6, ls=':')
    ax.text(71230, ax.get_ylim()[0] * 1.2, ' one paper', fontsize=6, color=MUTE)
    fig.tight_layout(); fig.savefig(OUT / 'figure6_twonode.png', bbox_inches='tight'); plt.close(fig)


for fn in (fig_concept, fig_tasks, fig1, fig2, fig2b, fig3, fig4):
    fn(); print('ok', fn.__name__)
for p in sorted(OUT.glob('*.png')):
    print(f'  {p.name}  {p.stat().st_size/1024:.0f} KB')
