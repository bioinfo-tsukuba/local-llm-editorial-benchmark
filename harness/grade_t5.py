#!/usr/bin/env python3
"""Grade T5. Recall over the 5 seeded figure defects; false positives on the compliant
figure (G3) are counted separately since that is the number an editor actually feels."""
import json, pathlib, re, csv, unicodedata
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
GT = {i['id']: i for i in json.loads((ROOT / 'data/groundtruth/T5_groundtruth.json').read_text())['items']}


def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(s or ''))).lower()


rows = defaultdict(lambda: {'detected': set(), 'fp_on_compliant': 0, 'raised': 0,
                            'wall_s': 0.0, 'errors': 0})
for f in sorted((ROOT / 'results/t5').glob('*.json')) if (ROOT / 'results/t5').exists() else []:
    r = json.loads(f.read_text())
    key = (r['model'], r['seed'])
    row = rows[key]
    d = r.get('defects') or []
    row['raised'] += len(d)
    row['wall_s'] += r.get('meta', {}).get('wall_s') or 0
    if r.get('error') or r.get('parse_error'):
        row['errors'] += 1
    item = GT[r['item']]
    texts = [norm(x.get('what') if isinstance(x, dict) else x) for x in d]
    if not item['defects']:
        row['fp_on_compliant'] += len(d)
        continue
    for dd in item['defects']:
        if any(sum(1 for k in dd['match_keywords'] if k.lower() in t) >= 1 for t in texts):
            row['detected'].add(dd['id'])

total = sum(len(i['defects']) for i in GT.values())
out = []
for (model, seed), r in sorted(rows.items()):
    out.append({'model': model, 'seed': seed, 'detected': len(r['detected']),
                'n_defects': total, 'recall': round(len(r['detected']) / total, 3),
                'fp_on_compliant_figure': r['fp_on_compliant'],
                'total_raised': r['raised'], 'wall_s_all_figures': round(r['wall_s'], 1),
                'errors': r['errors'],
                'found': ','.join(sorted(r['detected']))})
if out:
    with open(ROOT / 'results/t5_summary.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    for r in out:
        print(' | '.join(f'{k}={v}' for k, v in r.items()))
else:
    print('t5: no results')
