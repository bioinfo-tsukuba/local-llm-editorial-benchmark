#!/usr/bin/env python3
"""Renumber figures 3 and 4 in MS-B so the citation order is 1, 2, 3, 4.

Fixing V20 (Figure 3 never cited) by citing Figure 3 in the truncation paragraph left
MS-B citing Figure 4 before Figure 3 -- itself a violation of "number the figures in the
order of their appearance in the text". A model found this on the supposedly compliant
control, which is exactly what the control is for. Idempotent: exits if already fixed.
"""
import pathlib, sys

b = pathlib.Path('data/manuscripts/MS-B.md')
t = b.read_text()

if 'the clockwise direction (Figure 3).' in t:
    print('MS-B already renumbered; nothing to do'); sys.exit(0)

SWAPS = [
    ('the clockwise direction (Figure 4).', 'the clockwise direction (Figure 3).'),
    ('susceptibility change (Figure 3) identifies six', 'susceptibility change (Figure 4) identifies six'),
    ('Figure 3. Residue-level decomposition', 'Figure 4. Residue-level decomposition'),
    ('Figure 4. Perturbation-response susceptibility', 'Figure 3. Perturbation-response susceptibility'),
    ('  Fig3_heatmap.png      600 dpi, colour\n  Fig4_susceptibility.png   600 dpi, greyscale',
     '  Fig3_susceptibility.png   600 dpi, greyscale\n  Fig4_heatmap.png      600 dpi, colour'),
]
for old, new in SWAPS:
    if old not in t:
        sys.exit(f'pattern not found: {old[:60]!r}')
    t = t.replace(old, new, 1)

# put the two legends back in numerical order
i = t.index('Figure 4. Residue-level')
j = t.index('Figure 3. Perturbation-response')
k = t.index('\nFigure file list')
leg4, leg3 = t[i:j], t[j:k]
t = t[:i] + leg3.rstrip() + '\n\n' + leg4.rstrip() + '\n' + t[k:]
b.write_text(t)
print('MS-B: figures 3 and 4 renumbered; citation order is now 1,2,3,4')
