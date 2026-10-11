#!/usr/bin/env python3
"""Check that the Word file carries every change listed in docx-changes.md.

The revised manuscript is assembled by hand, so this compares the .docx back
against the markdown it was supposed to follow: for each changed passage, the new
wording must be present and the wording it replaced must be gone.

Comparison is on normalised text -- markdown markers stripped, curly quotes and
dashes folded, whitespace collapsed, case ignored -- because Word re-renders all of
those. Each passage is checked by its first and last sentence rather than whole,
since Word may split a paragraph the markdown wrapped differently.

Usage: python3 harness/check_docx_against_changes.py [file.docx]
"""
import difflib, pathlib, re, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAPER = ROOT / 'BPPB-special-issue-paper'
OLD = PAPER / '20260911_1st_submission' / 'manuscript.md'
NEW = PAPER / 'manuscript.md'
DOCX = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else PAPER / 'manuscript.docx'

FOLD = {'‘': "'", '’': "'", '“': '"', '”': '"',
        '–': '-', '—': '-', '−': '-', '×': 'x',
        '‑': '-', ' ': ' '}


def norm(t):
    for k, v in FOLD.items():
        t = t.replace(k, v)
    t = re.sub(r'[*`_#]', '', t)   # '#' so a markdown heading matches its Word text
    return re.sub(r'\s+', ' ', t).strip().lower()


def docx_text(p):
    z = zipfile.ZipFile(p)
    out = []
    for n in z.namelist():
        if re.match(r'word/(document|header\d*|footer\d*)\.xml$', n):
            x = z.read(n).decode('utf-8', 'ignore')
            # runs are joined with nothing: Word splits a word across runs at any
            # formatting boundary, and a separator turns "top left" into "top l eft"
            out.append(''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', x, re.S)))
    import html
    return norm(html.unescape(' '.join(out)))


def sentences(t):
    return [s.strip() for s in re.split(r'(?<=[.;:])\s+', t) if len(s.strip()) > 45]


def main():
    if not DOCX.exists():
        sys.exit(f'no such file: {DOCX}')
    body = docx_text(DOCX)
    a, b = OLD.read_text().split('\n'), NEW.read_text().split('\n')
    ops = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
           if o[0] != 'equal']
    bad, n = [], 0
    for tag, i1, i2, j1, j2 in ops:
        n += 1
        new = norm(' '.join(b[j1:j2]))
        old = norm(' '.join(a[i1:i2]))
        # a hunk often starts or ends mid-sentence where the markdown wrapped, so
        # probe the longest whole sentences inside it rather than its first characters
        ss = sorted(sentences(new), key=len, reverse=True)[:2] or [new]
        missing = [p for p in ss if p[:70] not in body]
        # the replaced wording must be gone; probe its distinctive opening
        stale = ''
        if old:
            os_ = sentences(old)
            for p in (os_ or [old]):
                if p[:70] and p[:70] in body and p[:70] not in new:
                    stale = p[:70]
                    break
        mark = 'ok  '
        if missing or stale:
            mark = 'FAIL'
            bad.append(n)
        print(f'{mark} [{n:2d}] {new[:64]}...')
        for p in missing:
            print(f'       new text not found: "{p[:70]}..."')
        if stale:
            print(f'       old text still present: "{stale}..."')

    # figures: compare the images Word embedded against the generated PNGs
    z = zipfile.ZipFile(DOCX)
    media = {z.read(m) for m in z.namelist() if m.startswith('word/media/')}
    figs = sorted((PAPER / 'figures').glob('figure*.png'))
    print()
    for f in figs:
        here = f.read_bytes() in media
        snap = PAPER / '20260911_1st_submission' / 'figures' / f.name
        changed = not snap.exists() or snap.read_bytes() != f.read_bytes()
        if changed:
            print(f'{"ok  " if here else "FAIL"} {f.name}: current version '
                  f'{"embedded" if here else "NOT embedded"} (changed this revision)')
            if not here:
                bad.append(f.name)
        elif not here:
            print(f'note {f.name}: unchanged this revision, embedded copy differs '
                  f'(re-exported by Word)')

    print()
    if bad:
        sys.exit(f'{len(bad)} item(s) not reflected in {DOCX.name}: {bad}')
    print(f'{DOCX.name} carries all {n} text changes')


if __name__ == '__main__':
    main()
