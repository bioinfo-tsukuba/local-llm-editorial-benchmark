#!/usr/bin/env python3
"""How many of the 40 seeded violations can plain code catch, with no model at all?

The benchmark kept showing the same split: models are good at reading the guideline
prose and matching it against the manuscript, and bad at cross-referencing and
counting. Cross-referencing and counting are exactly what a program does reliably.
This measures the boundary instead of asserting it -- if code catches most of the
mechanical half, the model only has to do the half it is actually good at, and the
"compliant manuscript costs 1.5x more tokens" problem largely disappears because the
model is handed a shorter job.

Deliberately dumb: regexes and arithmetic over the same plain-text manuscript the
models saw. No parsing of Word or LaTeX, which a real pipeline would have.
"""
import json, pathlib, re, sys

DPI_RE = r'(\d{2,3}) dpi'
ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(name):
    return (ROOT / f'data/manuscripts/{name}.md').read_text()


def sect(t, start, end):
    i = t.index(start) + len(start)
    return t[i:t.index(end, i)].strip()


def check(t):
    """Return {violation_id: (caught, evidence)} for what code alone can decide."""
    out = {}
    flat = re.sub(r'\s+', ' ', t)
    body = t[:t.index('\nFigure legends')] if '\nFigure legends' in t else t

    # --- counts -----------------------------------------------------------
    ab = sect(t, 'Abstract\n', '\nKeywords:')
    out['V02'] = (len(ab.split()) > 250, f'abstract {len(ab.split())} words')
    out['V03'] = (bool(re.search(r'\[\d+\]', ab)), 'citation in abstract')
    sig = sect(t, '\nSignificance\n', '\nIntroduction') if '\nSignificance\n' in t else ''
    out['V06'] = (bool(sig) and len(sig.split()) >= 100, f'significance {len(sig.split())} words')
    kw = re.search(r'Keywords: (.+)', t)
    n_kw = len(kw.group(1).split(',')) if kw else 0
    out['V05'] = (n_kw > 5, f'{n_kw} keywords')
    rt = re.search(r'Running title: (.+)', t)
    out['V07'] = (bool(rt) and len(rt.group(1)) > 50, f'running title {len(rt.group(1)) if rt else 0} chars')
    if 'Graphical abstract caption' in t:
        ga = sect(t, 'Graphical abstract caption\n', '\nReferences') if '\nReferences' in t[t.index('Graphical abstract caption'):] else ''
        ga = ga or t[t.index('Graphical abstract caption'):].split('\n\n')[1]
        out['V25'] = (len(ga.split()) >= 100, f'graphical abstract caption {len(ga.split())} words')

    # --- prohibited wording ----------------------------------------------
    title = t.split('\n\n')[2].strip().split('\n')[0] if len(t.split('\n\n')) > 2 else ''
    out['V01'] = (bool(re.search(r'\b(novel|new|first|unprecedented)\b', title, re.I)),
                  f'title: {title[:50]}')
    out['V04'] = ('for the first time' in ab.lower(), 'claim in abstract')

    # The graphical-abstract caption must not repeat the article title. A verbatim
    # first sentence is a string comparison, so it belongs here rather than in the
    # model's half of the work.
    if 'Graphical abstract caption' in t:
        cap = t[t.index('Graphical abstract caption'):].split('\n\n')[1].strip()
        first = re.split(r'(?<=[.!?])\s', cap)[0].strip().rstrip('.').lower()
        out['V26'] = (bool(title) and first.startswith(title.rstrip('.').lower()[:40]),
                      f'caption opens with the title: {first[:44]!r}')

    # --- required sections and their order -------------------------------
    order = ['Introduction', 'Materials and methods', 'Results', 'Discussion',
             'Conclusion', 'Conflict of interest', 'Author contributions',
             'Data availability', 'Acknowledgements', 'References']
    pos = {s: t.find('\n' + s + '\n') for s in order}
    out['V11'] = (pos['Data availability'] < 0, 'Data availability absent')
    out['V12'] = (pos['Conclusion'] < 0, 'Conclusion absent')
    present = [(s, p) for s, p in pos.items() if p >= 0]
    inversions = [(a[0], b[0]) for a, b in zip(present, present[1:]) if a[1] > b[1]]
    out['V10'] = (('Author contributions', 'Data availability') in inversions
                  or any(a == 'Author contributions' and b == 'Conflict of interest'
                         for a, b in [(x[0], y[0]) for x, y in zip(present, present[1:])])
                  or pos['Author contributions'] < pos['Conflict of interest'],
                  'Author contributions before Conflict of interest')
    out['V13'] = (pos['Acknowledgements'] > pos['References'] > 0,
                  'Acknowledgements after References')

    # --- cross-references: the models' weakest area -----------------------
    # A citation is a mention in running prose; the tables/figures block repeats
    # the labels as titles, so cut it off first.
    prose = body.split('\nTables\n')[0]
    for n in (1, 2, 3, 4):
        cited = re.search(rf'\(?(Table|Figure) {n}\)?', body)
    # A citation is a mention in running prose. "Table 1" also appears as the
    # table's own title, so strip the tables block before looking.
    tab_hits = [(m.start(), int(m.group(1))) for m in re.finditer(r'Table (\d)', prose)]
    tabs_cited = []
    for _, n in tab_hits:
        if n not in tabs_cited:
            tabs_cited.append(n)
    out['V15'] = (1 not in tabs_cited, f'tables cited in prose: {tabs_cited}')
    figs = [int(m.group(1)) for m in re.finditer(r'Figure (\d)', prose)]
    seen, order_ok = [], True
    for f in figs:
        if f not in seen:
            if seen and f != max(seen) + 1:
                order_ok = False
            seen.append(f)
    out['V21'] = (not order_ok, f'figure citation order in text: {figs}')
    out['V20'] = (3 not in figs, f'figures cited: {sorted(set(figs))}')
    out['V16'] = (bool(tabs_cited) and tabs_cited != sorted(tabs_cited[:1] + tabs_cited[1:])
                  or (bool(tabs_cited) and tabs_cited[0] != 1),
                  f'table citation order in prose: {tabs_cited}')

    # --- file lists -------------------------------------------------------
    out['V22'] = (bool(re.search(r'\b(\d{2,3}) dpi', t)) and
                  min(int(m) for m in re.findall(r'(\d{2,3}) dpi', t)) < 300,
                  # computed outside the f-string: a backslash in the expression
                  # part is a syntax error before Python 3.12
                  "dpi values: %s" % sorted(set(re.findall(DPI_RE, t))))
    out['V23'] = ('.bmp' in t, 'bmp figure file')
    out['V24'] = (bool(re.search(r'Graphical_abstract\.tiff|Graphical abstract.*\.tiff', t)),
                  'graphical abstract in TIFF')
    out['V28'] = ('.mov' in t, 'mov supplementary movie')
    # Only look at the supplementary/figure file lists, and only flag a name that
    # actually contains a multi-byte character or an embedded space before the
    # extension. The earlier broad pattern matched ordinary indented prose.
    # Pull out the file names themselves rather than whole lines: a line like
    # "Supplementary Figure S1 (SupplementaryFigureS1.pdf)" contains a space, but
    # the file name inside the parentheses does not.
    names = re.findall(r'[^\s()]*\.(?:tiff|png|pdf|zip|bmp|mpeg|mov|xlsx|jpe?g)\b', t)
    spaced = re.findall(r'(?:^|\s{2})([^\s()][^()\n]*?\s[^\s()]*\.'
                        r'(?:tiff|png|pdf|zip|bmp|mpeg|mov|xlsx|jpe?g))\b', t, re.M)
    bad = [n for n in names if re.search(r'[぀-ヿ一-鿿]', n)] + \
          [x for x in spaced if re.search(r'[぀-ヿ一-鿿]', x) or
           re.match(r'^[^\s]+\s\S*\.', x.strip())]
    out['V29'] = (bool(bad), f'file names with a space or multi-byte char: {bad[:2]}')
    mb = [int(m) for m in re.findall(r'\((\d+) MB\)', t)]
    out['V30'] = (any(v > 20 for v in mb), f'file sizes: {mb}')
    out['V27'] = (bool(re.search(r'Suppl_(Fig|Table|Movie)', t)), 'non-standard supplementary naming')

    # --- reference list ---------------------------------------------------
    nums = [int(m) for m in re.findall(r'^\[(\d+)\]', t, re.M)]
    out['V33'] = (nums != sorted(nums), f'reference numbering: {nums}')
    # the phrase is line-wrapped in the reference list ("In\npreparation.")
    out['V34'] = (bool(re.search(r'in\s+preparation', flat, re.I)), '"in preparation" in list')
    out['V35'] = (bool(re.search(r'^\[\d+\][^\n]*Personal communication', t, re.M | re.I)),
                  'personal communication in list')
    out['V31'] = (bool(re.search(r'interfaces\s*\n?\(\d+,\s*\d+\)', t)) or
                  bool(re.search(r'\(\d+, \d+\)\.', t)), 'parenthetical citation')
    out['V32'] = (bool(re.search(r'\(PDB \w{4}\)', t)), 'PDB not in prescribed form')
    out['V38'] = (bool(re.search(r'doi:10\.', t)), 'DOI not given as URL')
    # author-count rule: >6 authors must be truncated with et al.
    bad_authors = []
    for m in re.finditer(r'^\[(\d+)\] (.+?)\.\s[A-Z]', t, re.M | re.S):
        names = re.findall(r'[A-Z][a-z]+,\s+[A-Z]\.', m.group(2))
        if len(names) > 6 and 'et al' not in m.group(2):
            bad_authors.append(int(m.group(1)))
    out['V36'] = (bool(bad_authors), f'refs listing >6 authors in full: {bad_authors}')
    return out


def main():
    gt = json.loads((ROOT / 'data/groundtruth/MS-A_groundtruth.json').read_text())
    ids = [v['id'] for v in gt['violations']]
    what = {v['id']: v['what'] for v in gt['violations']}
    a, b = check(load('MS-A')), check(load('MS-B'))

    tp = [i for i in ids if a.get(i, (False,))[0]]
    fp = [i for i in ids if b.get(i, (False,))[0]]
    covered = sorted(a)
    print(f'コードだけで判定を試みた違反: {len(covered)}/40')
    print(f'違反原稿 MS-A で検出   : {len(tp)}/40  ({len(tp)/40:.0%})')
    print(f'適合原稿 MS-B で誤検出 : {len(fp)}   {fp}')
    print()
    print('--- 検出できた ---')
    for i in tp:
        print(f'  {i}  {a[i][1]:44s} {what[i][:58]}')
    print('--- 判定を試みたが検出できなかった ---')
    for i in covered:
        if i not in tp:
            print(f'  {i}  {a[i][1]:44s} {what[i][:58]}')
    print('--- そもそもコードでは判定不能 ---')
    for i in ids:
        if i not in covered:
            print(f'  {i}  {what[i][:88]}')


if __name__ == '__main__':
    main()
