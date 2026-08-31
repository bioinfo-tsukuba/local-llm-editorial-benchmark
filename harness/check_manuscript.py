#!/usr/bin/env python3
"""Check the manuscript against the BPPB limits before submission.

Counts words the way a journal does — whitespace-separated tokens, so that
numerals such as "3.3" and "39.6%" count. An earlier check used a
letter-initial regex, which undercounted the abstract by 22 words and reported
it as within limit when it was 257.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The paper lives in BPPB-special-issue-paper/ in the working repository and in
# paper/ in the public release, which is assembled by harness/make_public_release.py.
# Resolving it here is what lets these checkers run in both trees.
PAPER = (ROOT / 'BPPB-special-issue-paper' if (ROOT / 'BPPB-special-issue-paper').is_dir()
         else ROOT / 'paper')
MS = PAPER / 'manuscript.md'
BANNED = ('new', 'novel', 'first', 'unprecedented')


def strip(t):
    t = re.sub(r'\*\(.*?\)\*', '', t, flags=re.S)     # editorial notes
    t = re.sub(r'^#+ .*$', '', t, flags=re.M)         # headings
    return t.strip()


def main():
    s = MS.read_text()
    fails = []

    ab = strip(s[s.index('## Abstract'):s.index('**Key words')])
    sig = strip(s[s.index('## ◀ Significance ▶'):s.index('---\n\n## Introduction')])
    kw = [k.strip() for k in s[s.index('**Key words:**'):].split('\n')[0]
          .replace('**Key words:**', '').split(',') if k.strip()]

    for label, n, lim in (('Abstract', len(ab.split()), 250),
                          ('Significance', len(sig.split()), 100),
                          ('Key words', len(kw), 5)):
        ok = n <= lim
        print(f'{label:<14}{n:>4} / {lim}   {"ok" if ok else "OVER"}')
        if not ok:
            fails.append(f'{label} {n} > {lim}')

    hits = [w for b in BANNED for w in re.findall(r'\b' + b + r'\w*', ab, re.I)]
    print(f'{"Banned words":<14}{len(hits):>4}       {"ok" if not hits else hits}')
    if hits:
        fails.append(f'banned words in abstract: {hits}')

    # references: cited set == listed set, numbered in order of first citation
    body = s[:s.index('## References')]
    order = []
    for m in re.findall(r'\[(\d+(?:,\d+)*)\]', body):
        for n in m.split(','):
            if int(n) not in order:
                order.append(int(n))
    listed = [int(m) for m in re.findall(r'^(\d+)\. ', s, re.M)]
    checks = [('cited == listed', sorted(order) == listed),
              ('numbered in citation order', order == sorted(order)),
              ('list contiguous from 1', listed == list(range(1, len(listed) + 1)))]
    for label, ok in checks:
        print(f'{label:<28}{"ok" if ok else "FAIL"}')
        if not ok:
            fails.append(label)
    print(f'{"references":<28}{len(listed)}')

    # the reference list must not contain a duplicate number: appending an entry
    # by hand once silently overwrote two existing works, leaving citations
    # pointing at the wrong papers
    all_nums = re.findall(r'^(\d+)\. ', s[s.index('## References'):], re.M)
    dup = {n for n in all_nums if all_nums.count(n) > 1}
    print(f'{"no duplicate entry numbers":<28}{"ok" if not dup else sorted(dup)}')
    if dup:
        fails.append(f'duplicate reference numbers {sorted(dup)}')

    # graphical abstract: file, resolution and caption length
    ga = PAPER / 'figures' / 'graphical_abstract.png'
    cap = PAPER / 'graphical-abstract-caption.txt'
    print(f'{"graphical abstract":<28}{"ok" if ga.exists() else "MISSING"}')
    if not ga.exists():
        fails.append('graphical abstract missing')
    if cap.exists():
        n = len(cap.read_text().split())
        ok = n < 100                      # the journal says "less than 100 words"
        print(f'{"  its caption":<28}{n:>4} / <100   {"ok" if ok else "OVER"}')
        if not ok:
            fails.append(f'graphical-abstract caption {n} >= 100')
    else:
        print(f'{"  its caption":<28}MISSING')
        fails.append('graphical-abstract caption missing')

    # every figure must be embedded with a legend, and the file must exist
    figs = re.findall(r'!\[Figure (\d+b?)\]\((figures/[^)]+)\)', s)
    legs = set(re.findall(r'^\*\*Figure (\d+b?)\*\*', s, re.M))
    cited = set(re.findall(r'\(Figures? (\d+b?)(?: and (\d+b?))?\)', s)[0]) if False else \
        {n for pair in re.findall(r'\(Figures? (\d+b?)(?: and (\d+b?))?\)', s) for n in pair if n}
    missing_file = [f for _, f in figs if not (PAPER / f).exists()]
    print(f'{"figures embedded":<28}{len(figs)}')
    for label, ok, detail in (
            ('every figure has a legend', {n for n, _ in figs} <= legs, ''),
            ('every legend has a figure', legs <= {n for n, _ in figs}, ''),
            ('every figure is cited', {n for n, _ in figs} >= cited, sorted(cited - {n for n, _ in figs})),
            ('figure files present', not missing_file, missing_file)):
        print(f'{label:<28}{"ok" if ok else "FAIL"} {detail if not ok else ""}')
        if not ok:
            fails.append(label)

    # Tables must be numbered in the order they are first cited, and each legend must
    # appear in the same order. This went unchecked while only the figures were, and
    # Table 4 -- the seed table in the Methods -- was cited before Tables 2 and 3.
    # One "Table 2" in the Results is MS-A's own table, not this paper's, and is
    # excluded by matching only citations in parentheses and bold legends.
    tbl_legs = re.findall(r'^\*\*Table (\d+)\*\*', s, re.M)
    tbl_cites, seen = [], set()
    for m in re.finditer(r'\(Tables? (\d+)(?: and (\d+))?\)', s):
        for n in m.groups():
            if n and n not in seen:
                seen.add(n); tbl_cites.append(n)
    for label, got in (('tables in citation order', tbl_cites),
                       ('table legends in order', tbl_legs)):
        ok = got == sorted(got, key=int)
        print(f'{label:<28}{"ok" if ok else "FAIL"} {"" if ok else got}')
        if not ok:
            fails.append(label)
    ok = set(tbl_legs) == set(tbl_cites)
    print(f'{"every table cited":<28}{"ok" if ok else "FAIL"} '
          f'{"" if ok else sorted(set(tbl_legs) ^ set(tbl_cites))}')
    if not ok:
        fails.append('table citations and legends disagree')

    # tables must have a constant column count
    blk, bad = [], []
    for i, line in enumerate(s.split('\n'), 1):
        if line.startswith('|'):
            blk.append((i, line.count('|')))
        else:
            if blk and len({c for _, c in blk}) > 1:
                bad.append(blk[-1][0])
            blk = []
    print(f'{"malformed tables":<28}{bad if bad else "none"}')
    if bad:
        fails.append(f'malformed tables at lines {bad}')

    print()
    if fails:
        sys.exit('FAILED: ' + '; '.join(fails))
    print('all checks pass')


if __name__ == '__main__':
    main()
