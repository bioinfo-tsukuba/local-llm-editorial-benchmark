#!/usr/bin/env python3
"""Produce the plain-text Instructions for Authors given to the models.

The original cleaning was done ad hoc and truncated the document after the
section on reprints, dropping the Copyright section and the whole of
"9. Corrections and retraction policy" (558 words) together with the trailing
version line. This script regenerates the file from the retrieved page, keeps
the document whole, and is checked against markers that must be present.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data/guidelines/bppb_instructions.txt'
OUT = ROOT / 'data/guidelines/bppb_instructions_clean.txt'

# Site navigation that precedes the document proper, and the footer after it.
START = 'Instructions for Authors'
NAV_END = 'Biophysics and Physicobiology (BPPB) is the official online open journal'
FOOTER = ('Previous Page', 'Scroll up', '© Biophysics and Physicobiology')

# Must survive cleaning; the truncation went unnoticed because nothing checked.
REQUIRED = ['Revised 21 August, 2026', 'Expression of Concern', 'Corrections and retraction',
            'Errata', 'Corrigenda', 'Addenda', 'Copyright',
            'Abstract', 'Significance', 'References', 'Figures and Tables']


def main():
    raw = SRC.read_text(errors='ignore')

    i = raw.find(NAV_END)
    if i < 0:
        sys.exit('could not locate the start of the document body')
    body = raw[i:]

    for f in FOOTER:                       # cut the site footer, keep the version line
        j = body.find(f)
        if j > 0:
            body = body[:j]

    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n{3,}', '\n\n', body)
    body = '\n'.join(line.strip() for line in body.split('\n'))
    body = re.sub(r'\n{3,}', '\n\n', body).strip() + '\n'
    body = 'Instructions for Authors\n\n' + body

    missing = [m for m in REQUIRED if m not in body]
    if missing:
        sys.exit(f'cleaning dropped required content: {missing}')

    OUT.write_text(body)
    words = len(re.findall(r"[A-Za-z][A-Za-z'-]*", body))
    print(f'{OUT.relative_to(ROOT)}  {words:,} words, {len(body):,} chars')
    print('all required markers present, including the version line')


if __name__ == '__main__':
    main()
