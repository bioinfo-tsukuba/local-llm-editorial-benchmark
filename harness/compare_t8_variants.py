#!/usr/bin/env python3
"""R2-3: T8 single call (variant A) against one reference per call (variant B).

Reports the paired per-model change on each of T8's four scored measures, and the
operational failure modes that are not scores: how many models never called a tool,
and how many produced no parseable answer. A null result is as reportable as a
positive one, so everything is printed whichever way it falls.

Usage: python3 harness/compare_t8_variants.py
"""
import csv, json, pathlib, statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
# denominators as grade_t8.py counts them, not as the Methods paragraph describes
# the item set: mismatch_caught is out of 3 because the grader folds the
# preprint-with-a-published-version item (V8) in with the two mismatches (V5, V7)
MEASURES = [('abbrev_correct', 4), ('mismatch_caught', 3),
            ('refusal_correct', 1)]


def load(name):
    p = ROOT / f'results/{name}_summary.csv'
    if not p.exists():
        raise SystemExit(f'missing {p}; run grade_t8.py {name.replace("_summary","")}')
    return {r['model']: r for r in csv.DictReader(p.open())}


def num(v):
    return int(str(v).split('/')[0])


def main():
    A, B = load('t8'), load('t8b')
    models = [m for m in A if m in B]
    print(f'{len(models)} models measured under both\n')

    for col, den in MEASURES:
        a = {m: num(A[m][col]) for m in models}
        b = {m: num(B[m][col]) for m in models}
        up = [m for m in models if b[m] > a[m]]
        dn = [m for m in models if b[m] < a[m]]
        same = len(models) - len(up) - len(dn)
        print(f'{col} (of {den}): one-call total {sum(a.values())}, '
              f'per-reference total {sum(b.values())}')
        print(f'   {len(up)} up, {len(dn)} down, {same} unchanged')
        for m in up:
            print(f'      + {m}: {a[m]} -> {b[m]}')
        for m in dn:
            print(f'      - {m}: {a[m]} -> {b[m]}')
        print()

    print('fabricated DOIs:',
          f"one-call {sum(int(A[m]['fabricated_dois']) for m in models)},",
          f"per-reference {sum(int(B[m]['fabricated_dois']) for m in models)}")

    def never(d):
        return [m for m in models if num(d[m]['n_tool_calls']) == 0]
    print('never called a tool: one-call', len(never(A)), '/ per-reference', len(never(B)))

    def noans(d):
        return [m for m in models if not str(d[m].get('n_checks') or '').strip()
                or num(d[m].get('n_checks') or 0) == 0]
    print('no parseable answer: one-call', len(noans(A)), '/ per-reference', len(noans(B)))

    wa = [float(A[m]['wall_s']) for m in models if A[m]['wall_s']]
    wb = [float(B[m]['wall_s']) for m in models if B[m]['wall_s']]
    if wa and wb:
        print(f'wall time, median: one-call {st.median(wa):.0f}s, '
              f'per-reference {st.median(wb):.0f}s '
              f'({st.median(wb)/st.median(wa):.1f}x)')
        print(f'wall time, total:  one-call {sum(wa)/60:.0f} min, '
              f'per-reference {sum(wb)/60:.0f} min')

    # the comparison the manuscript will quote, in one line per model
    print('\nper model, abbrev_correct:')
    for m in sorted(models, key=lambda m: -num(B[m]['abbrev_correct'])):
        print(f"   {m:30s} {num(A[m]['abbrev_correct'])} -> {num(B[m]['abbrev_correct'])}")


if __name__ == '__main__':
    main()
