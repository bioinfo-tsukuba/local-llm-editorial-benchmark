#!/usr/bin/env python3
"""Grade T8. Separates the failure modes that matter operationally:

  abbrev_correct   the Index Medicus abbreviation the journal requires
  mismatch_caught  noticed that a resolving DOI points at a different paper,
                   or that volume/year disagree with the record
  refusal_correct  reported the fabricated reference as unverifiable
  FABRICATED       stated a DOI, abbreviation, volume or year that no tool
                   returned -- the failure this task exists to detect
"""
import csv, json, pathlib, re, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
GT = {i['id']: i for i in json.loads((ROOT / 'data/t8/items.json').read_text())['items']}


def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(s or ''))).strip().lower()


def txt(c):
    return norm(f"{c.get('journal_abbreviated')} {' '.join(map(str, c.get('problems') or []))} "
                f"{c.get('corrected_doi')}")


rows = []
d = ROOT / 'results' / 't8'
for f in sorted(d.glob('*.json')) if d.exists() else []:
    r = json.loads(f.read_text())
    checks = {str(c.get('id')).upper(): c for c in (r.get('checks') or []) if isinstance(c, dict)}
    tool_dois = {norm(t['args'].get('doi')) for t in r.get('tool_trace', [])
                 if t.get('tool') == 'lookup_doi'}
    returned = ' '.join(norm(t.get('result_summary')) for t in r.get('tool_trace', []))

    abbrev_ok = abbrev_n = 0
    caught = caught_n = 0
    refusal = refusal_n = 0
    fabricated = []
    detail = []
    for vid, spec in GT.items():
        c = checks.get(vid)
        e = spec['expect']
        if 'abbrev' in e:
            abbrev_n += 1
            if c and norm(c.get('journal_abbreviated')) == norm(e['abbrev']):
                abbrev_ok += 1
            else:
                detail.append(f"{vid}:abbrev={c.get('journal_abbreviated') if c else 'absent'!r}")
        if e.get('mismatch'):
            caught_n += 1
            hit = c and (c.get('verified') is False or c.get('problems'))
            if hit:
                caught += 1
            else:
                detail.append(f'{vid}:mismatch-missed')
        if e.get('found') is False:
            refusal_n += 1
            if c and c.get('verified') is False and not c.get('corrected_doi'):
                refusal += 1
            else:
                detail.append(f'{vid}:FABRICATED-or-claimed-verified')
        if e.get('published_version_exists'):
            caught_n += 1
            if c and (c.get('problems') or c.get('corrected_doi')):
                caught += 1
            else:
                detail.append(f'{vid}:published-version-missed')
        # any DOI asserted that no tool returned
        if c and c.get('corrected_doi'):
            cd = norm(c['corrected_doi'])
            if cd and cd not in returned:
                fabricated.append(f'{vid}:{c["corrected_doi"]}')

    rows.append({
        'model': r['model'], 'seed': r['seed'],
        'error': r.get('error') or r.get('parse_error') or '',
        'n_tool_calls': r.get('n_tool_calls'), 'n_checks': r.get('n_checks'),
        'abbrev_correct': f'{abbrev_ok}/{abbrev_n}',
        'mismatch_caught': f'{caught}/{caught_n}',
        'refusal_correct': f'{refusal}/{refusal_n}',
        'fabricated_dois': len(fabricated),
        'fabricated_detail': ';'.join(fabricated),
        'wall_s': r.get('wall_s'), 'peak_vram_mib': r.get('meta', {}).get('peak_size_vram_mib'),
        'detail': ';'.join(detail),
    })

if rows:
    with open(ROOT / 'results/t8_summary.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    hdr = ['model', 'n_tool_calls', 'abbrev_correct', 'mismatch_caught',
           'refusal_correct', 'fabricated_dois', 'wall_s']
    print(' | '.join(f'{h:>15.15s}' for h in hdr))
    for r in rows:
        print(' | '.join(f'{str(r.get(h,"")):>15.15s}' for h in hdr))
    print()
    for r in rows:
        if r['detail']:
            print(f"  {r['model'][:30]}: {r['detail']}")
else:
    print('t8: no results')
