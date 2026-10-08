#!/usr/bin/env python3
"""Assemble the point-by-point response from the per-comment files.

The letter is written one comment per file under
BPPB-special-issue-paper/20261008_1st_revision/R2R/ and concatenated here, so the
version pasted into ScholarOne cannot drift from the files that were reviewed.
Order comes from the table in R2R/README.md, which is the numbering itself.

Usage: python3 harness/make_r2r.py
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
R2R = ROOT / 'BPPB-special-issue-paper/20261008_1st_revision/R2R'
OUT = ROOT / 'BPPB-special-issue-paper/20261008_1st_revision/response-to-reviewers.md'

HEAD = """# Response to the reviewers\' comments

Manuscript BSJ-2026053, "Benchmarking locally hosted language models for journal
editorial work on a compact desktop workstation".

We thank both reviewers for reading the manuscript closely and for recommending
publication. Every point is answered below in the order it appears in the decision
letter, with the comment quoted in full and the change it produced named. Where a
comment asked for something we did not do, we say so and say why.

## List of changes

| Comment | Change |
|---|---|
| R1-1 | Materials and methods: added what T4 corresponds to in editorial work. Results: added the T4 outcome. Figure 2 legend: one clause to the same effect. |
| R1-2 | Figure 1 re-laid out; the overlapping caption and one further overflow are gone. |
| R1-3 | Figure 2: the T5 item relabelled "72 dpi (300 required)"; legend states that the list is of seeded defects, not requirements. |
| R1-4 | Figure 7: token-count annotations moved off the y axis. |
| R2-1 | Discussion: added what fine-tuning on the checker\'s output would require, and that we did not test it. |
| R2-2 | Materials and methods: the eight checklist areas listed. |
| R2-3 | **New measurement.** The decomposition was run on T8. Results: a new paragraph; Figure 6: a fourth panel; Materials and methods: the T8 arm and the completed description of the T8 item set; Discussion: the limits of the two-task comparison. |
| R2-4 | KV cache, TCP, RoCE, RPC and VRAM expanded at first use. |

---

"""


def quoted_blocks(text):
    """Blockquotes other than the one holding the reviewer's comment."""
    out, cur = [], []
    for line in text.split('\n'):
        if line.startswith('>'):
            cur.append(line[1:].strip())
        elif cur:
            out.append(' '.join(x for x in cur if x)); cur = []
    if cur:
        out.append(' '.join(x for x in cur if x))
    return [b for b in out if '**Comment R' not in b]


def check_quotes(ids):
    """Every passage the letter quotes must be in the manuscript word for word.

    The letter tells the reviewers what the manuscript now says. If the two drift the
    letter becomes a claim about a text that does not exist, which is the one error
    this file cannot be allowed to make.
    """
    ms = ' '.join((ROOT / 'BPPB-special-issue-paper/manuscript.md').read_text().split())
    bad = []
    for cid in ids:
        for q in quoted_blocks((R2R / f'{cid}.md').read_text()):
            # ** marks the wording this revision added; the manuscript has no such
            # markers, so they come out before the comparison
            plain = ' '.join(q.replace('**', '').split())
            if plain not in ms:
                bad.append((cid, plain[:90]))
    for cid, q in bad:
        print(f'  NOT IN MANUSCRIPT  {cid}: {q}...')
    return not bad


def main():
    ids = re.findall(r'\[(R\d-\d)\.md\]\(', (R2R / 'README.md').read_text())
    if not ids:
        sys.exit('no comment ids found in R2R/README.md')
    parts = [HEAD]
    for cid in ids:
        f = R2R / f'{cid}.md'
        if not f.exists():
            sys.exit(f'missing {f}')
        body = f.read_text().strip()
        # the per-file notes to ourselves never go to the journal
        body = body.split('\n---\n\n**Note for the author')[0].rstrip()
        parts.append(body + '\n\n---\n')
    if not check_quotes(ids):
        sys.exit('a quoted passage is not in the manuscript')
    OUT.write_text('\n'.join(parts).rstrip() + '\n')
    n = len(OUT.read_text().split())
    print(f'wrote {OUT.relative_to(ROOT)}: {len(ids)} comments, {n} words')
    print('   ' + ', '.join(ids))


if __name__ == '__main__':
    main()
