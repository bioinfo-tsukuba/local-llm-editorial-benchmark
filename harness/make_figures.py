#!/usr/bin/env python3
"""Generate T5 (VLM) figure assets with known, checkable defects.

Each figure pairs with a legend in data/groundtruth/T5_groundtruth.json. The defects are
the kind an editor actually catches by eye: panel labels that disagree with the legend,
resolution below the journal minimum, unreadable axis text, and a table with vertical
rules (which BPPB forbids).
"""
import pathlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = pathlib.Path('data/figures'); OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
x = np.linspace(0, 10, 200)


def panel(ax, kind, label, labelsize=11):
    if kind == 'decay':
        ax.plot(x, np.exp(-x / 2.3), lw=1.6)
        ax.plot(x, np.exp(-x / 0.7), lw=1.6, ls='--')
        ax.set_xlabel('subunit separation'); ax.set_ylabel('susceptibility')
    elif kind == 'spectrum':
        ax.bar(np.arange(1, 21), np.sort(rng.random(20)) * 3 + 0.2, width=0.7)
        ax.set_xlabel('mode index'); ax.set_ylabel('frequency (a.u.)')
    else:
        ax.imshow(rng.random((12, 12)), cmap='viridis')
        ax.set_xlabel('residue i'); ax.set_ylabel('residue j')
    ax.tick_params(labelsize=labelsize)
    ax.xaxis.label.set_size(labelsize); ax.yaxis.label.set_size(labelsize)
    ax.text(-0.18, 1.06, label, transform=ax.transAxes, fontsize=labelsize + 3,
            fontweight='bold', va='top')


# FIG-1: panel labels (a) and (c); the legend describes (a) and (b)  -> mismatch
fig, axs = plt.subplots(1, 2, figsize=(7, 3), constrained_layout=True)
panel(axs[0], 'decay', '(a)')
panel(axs[1], 'spectrum', '(c)')
fig.savefig(OUT / 'FIG-1_panel_label_mismatch.png', dpi=300)
plt.close(fig)

# FIG-2: 72 dpi and 5 pt axis text -> below the 300 dpi minimum, unreadable
fig, axs = plt.subplots(1, 2, figsize=(7, 3), constrained_layout=True)
panel(axs[0], 'decay', '(a)', labelsize=5)
panel(axs[1], 'heat', '(b)', labelsize=5)
fig.savefig(OUT / 'FIG-2_low_resolution.png', dpi=72)
plt.close(fig)

# FIG-3: compliant control -- 300 dpi, readable, labels match the legend
fig, axs = plt.subplots(1, 3, figsize=(10, 3), constrained_layout=True)
for ax, k, l in zip(axs, ['decay', 'spectrum', 'heat'], ['(a)', '(b)', '(c)']):
    panel(ax, k, l)
fig.savefig(OUT / 'FIG-3_compliant.png', dpi=300)
plt.close(fig)

# FIG-4: a table rendered as an image, with vertical rules (BPPB forbids them)
fig, ax = plt.subplots(figsize=(6, 2.4)); ax.axis('off')
cell = [['2.0', '2.05', '0.74', '2.77'], ['2.4', '2.19', '0.72', '3.04'],
        ['2.8', '2.31', '0.70', '3.30'], ['3.2', '2.42', '0.69', '3.51']]
tb = ax.table(cellText=cell, colLabels=['s', 'CCW', 'CW', 'ratio'], loc='center')
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.5)
for (r, c), cellobj in tb.get_celld().items():
    cellobj.set_linewidth(0.8)          # keeps all four edges -> vertical rules present
fig.savefig(OUT / 'FIG-4_table_vertical_rules.png', dpi=300, bbox_inches='tight')
plt.close(fig)

for p in sorted(OUT.glob('*.png')):
    from PIL import Image
    im = Image.open(p)
    print(f'{p.name:38s} {im.size[0]}x{im.size[1]} px  dpi={im.info.get("dpi")}  '
          f'{p.stat().st_size/1024:.0f} KB')
