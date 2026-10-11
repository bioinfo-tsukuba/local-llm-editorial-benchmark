#!/usr/bin/env python3
"""Render the point-by-point response to PDF for upload to ScholarOne.

The decision letter allows the response either typed into the form or uploaded as a
file. This produces the file. There is no pandoc on this machine, so the markdown is
converted to a self-contained HTML and LibreOffice converts that to PDF.

Only the constructs the letter actually uses are handled: headings, horizontal rules,
tables, blockquotes with bullets inside them, bold, and inline code. Anything else
would silently pass through, so the script refuses to run if it meets a line it does
not recognise as one of those.

Usage: python3 harness/make_r2r_pdf.py
"""
import html, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'BPPB-special-issue-paper/20261011_1st_revision/response-to-reviewers.md'
OUTDIR = SRC.parent

CSS = """
@page { size: A4; margin: 22mm 20mm; }
body { font-family: 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.45;
       color: #000; }
h1 { font-size: 15pt; margin: 0 0 10pt 0; }
h2 { font-size: 12pt; margin: 16pt 0 6pt 0; }
p { margin: 0 0 7pt 0; text-align: justify; }
hr { border: 0; border-top: .6pt solid #999; margin: 14pt 0; }
blockquote { margin: 7pt 0 9pt 10pt; padding: 0 0 0 9pt;
             border-left: 2.2pt solid #bbb; color: #222; }
blockquote p { margin: 0 0 5pt 0; }
blockquote ul { margin: 3pt 0 5pt 16pt; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; font-size: 9.5pt; }
th, td { border-bottom: .5pt solid #ccc; padding: 3pt 5pt; text-align: left;
         vertical-align: top; }
th { border-bottom: .9pt solid #666; }
td:first-child, th:first-child { white-space: nowrap; width: 16mm; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; }
"""


def inline(t):
    t = html.escape(t)
    # a comment id must not break across lines at its hyphen, which is what the
    # narrow first table column did to every row ("R1-" above "1")
    t = re.sub(r'\bR([12])-(\d)\b', 'R\\1\u2011\\2', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    return t


def convert(md):
    out, i, lines = [], 0, md.split('\n')
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ln.startswith('## '):
            out.append(f'<h2>{inline(ln[3:])}</h2>'); i += 1
        elif ln.startswith('# '):
            out.append(f'<h1>{inline(ln[2:])}</h1>'); i += 1
        elif ln.strip() == '---':
            out.append('<hr/>'); i += 1
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
            cells = [c for c in cells if not all(set(x) <= set('-: ') for x in c)]
            head, body = cells[0], cells[1:]
            out.append('<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head)
                       + '</tr>' + ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>'
                                                            for c in r) + '</tr>'
                                           for r in body) + '</table>')
        elif ln.startswith('>'):
            block = []
            while i < len(lines) and lines[i].startswith('>'):
                block.append(lines[i][1:].strip()); i += 1
            out.append('<blockquote>' + para(block) + '</blockquote>')
        else:
            block = []
            while i < len(lines) and lines[i].strip() \
                    and not lines[i].startswith(('>', '|', '#')) \
                    and lines[i].strip() != '---':
                block.append(lines[i].strip()); i += 1
            out.append(para(block))
    return '\n'.join(out)


def para(block):
    """A run of lines into paragraphs and bullet lists."""
    out, buf, bullets = [], [], []

    def flush():
        if buf:
            out.append(f'<p>{inline(" ".join(buf))}</p>'); buf.clear()
        if bullets:
            out.append('<ul>' + ''.join(f'<li>{inline(b)}</li>' for b in bullets)
                       + '</ul>'); bullets.clear()
    for ln in block:
        if not ln:
            flush(); continue
        if ln.startswith(('* ', '- ')):
            if buf:
                out.append(f'<p>{inline(" ".join(buf))}</p>'); buf.clear()
            bullets.append(ln[2:])
        else:
            if bullets:
                out.append('<ul>' + ''.join(f'<li>{inline(b)}</li>' for b in bullets)
                           + '</ul>'); bullets.clear()
            buf.append(ln)
    flush()
    return ''.join(out)


def main():
    md = SRC.read_text()
    body = convert(md)
    if '**' in body or re.search(r'(?<!<)`', body):
        sys.exit('unconverted markdown left in the output')
    htm = OUTDIR / 'response-to-reviewers.html'
    htm.write_text(f'<html><head><meta charset="utf-8"><title>'
                   f'Response to the reviewers’ comments</title>'
                   f'<style>{CSS}</style></head><body>{body}</body></html>')
    r = subprocess.run(['soffice', '--headless', '--convert-to', 'pdf',
                        '--outdir', str(OUTDIR), str(htm)],
                       capture_output=True, text=True, timeout=300)
    pdf = OUTDIR / 'response-to-reviewers.pdf'
    if not pdf.exists():
        sys.exit(f'conversion failed: {r.stdout}{r.stderr}')
    htm.unlink()
    n = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout
    pages = re.search(r'Pages:\s+(\d+)', n)
    print(f'wrote {pdf.relative_to(ROOT)}  '
          f'{pdf.stat().st_size / 1024:.0f} KB, {pages.group(1) if pages else "?"} pages')


if __name__ == '__main__':
    main()
