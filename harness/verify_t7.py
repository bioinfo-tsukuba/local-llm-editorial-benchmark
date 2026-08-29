#!/usr/bin/env python3
"""Verify MS-E: the five category exemptions really are absent, and the eight rules that
still apply really are violated.

T7 measures a false-positive rate, so the exempt items must be unambiguously absent --
if the manuscript contained something abstract-shaped, a model flagging it would not be
making the error the test is trying to detect.
"""
import re, sys, pathlib

t = (pathlib.Path(__file__).resolve().parent.parent / 'data/manuscripts/MS-E.md').read_text()
flat = re.sub(r'\s+', ' ', t)
bad = []


def chk(name, cond, msg):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}: {msg}")
    if not cond:
        bad.append(name)


print('=== category declared ===')
chk('CAT', 'Commentary and Perspective]' in t, 'declared as Commentary and Perspective')

print('\n=== the five exemptions: these must be ABSENT (flagging them is the error) ===')
chk('X01', not re.search(r'^Abstract\s*$', t, re.M), 'no Abstract section')
chk('X02', not re.search(r'^Significance', t, re.M), 'no Significance statement')
chk('X03', 'Running title' not in t, 'no Running title')
chk('X04', 'raphical abstract' not in t and 'Graphical_abstract' not in t, 'no graphical abstract')
chk('X05', not re.search(r'^(Materials and methods|Methods|Results)\s*$', t, re.M),
    'no Materials and methods / Results sections')

print('\n=== the eight rules that still apply: these must be VIOLATED ===')
chk('A01', 'Novel directions' in t, 'title contains the prohibited word "Novel"')
chk('A02', '(1, 2)' in t, 'in-text citation uses parentheses instead of brackets')
chk('A03', 'In preparation' in t, 'reference [5] is "In preparation"')
order = re.findall(r'^\[(\d+)\]', t, re.M)
chk('A04', order != sorted(order, key=int), f'reference list out of numerical order: {order}')
chk('A05', re.search(r'Study\s+\|', t) is not None, 'Table 1 uses vertical lines')
chk('A06', '150 dpi' in t, 'figure supplied at 150 dpi')
chk('A07', '.bmp' in t, 'figure supplied as .bmp')
chk('A08', re.search(r'図1_draft version', t) is not None,
    'supplementary file name contains a Japanese character and a space')

print('\n=== end matter present and in order (no ambiguity to trip over) ===')
pos = [(s, t.find('\n' + s + '\n')) for s in
       ['Conflict of interest', 'Author contributions', 'Data availability',
        'Acknowledgements', 'References']]
for s, p in pos:
    chk(f'ORD-{s[:12]}', p >= 0, f'{s} present at {p}')
chk('ORD', all(pos[i][1] < pos[i + 1][1] for i in range(len(pos) - 1)),
    'end matter in the prescribed order')
chk('KW', len(re.search(r'Keywords: (.+)', t).group(1).split(',')) <= 5,
    'at most five keywords (the keyword rule is worded "below the abstract", so a '
    'compliant count avoids an ambiguity this test is not about)')

print(f'\n{len(bad)} problem(s): {bad}')
sys.exit(1 if bad else 0)
