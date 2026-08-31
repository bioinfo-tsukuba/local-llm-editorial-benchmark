#!/usr/bin/env python3
"""Grade T2/T3/T4 results. Writes results/<task>_summary.csv and an adjudication file
for anything the automatic rules cannot settle.
"""
import json, pathlib, re, csv, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(p):
    return json.loads((ROOT / p).read_text())


# The journal's own reference examples use en-dashes ("709-715" is printed as
# "709\u2013715"), and models reproduce them, plus non-breaking hyphens inside words.
# Fold every dash-like codepoint to ASCII '-' so a correct conversion is not scored wrong
# on typography.
DASHES = dict.fromkeys(map(ord, '\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uff0d'), '-')


def norm(s):
    s = unicodedata.normalize('NFKC', str(s or '')).translate(DASHES)
    return re.sub(r'\s+', ' ', s).lower()


# ------------------------------------------------------------------ T2
def grade_t2(rec, adj):
    gt = load('data/groundtruth/T2_review_points.json')
    pts = rec.get('weaknesses') or []
    texts = [norm(f"{p.get('topic','')} {p.get('point','')}") if isinstance(p, dict) else norm(p)
             for p in pts]
    matched, used = {}, set()
    cand = []
    for gi, g in enumerate(gt['points']):
        for fi, t in enumerate(texts):
            h = [k for k in g['match_keywords'] if k.lower() in t]
            if h:
                cand.append((len(h), gi, fi, h))
    cand.sort(reverse=True)
    for n, gi, fi, h in cand:
        if gi in matched or fi in used:
            continue
        matched[gi] = (fi, h); used.add(fi)
    for fi, p in enumerate(pts):
        if fi not in used:
            adj.write(json.dumps({'task': 't2', 'model': rec['model'], 'unmatched_point': p},
                                 ensure_ascii=False) + '\n')
    cons = [i for i, g in enumerate(gt['points']) if len(g['reviewers']) >= 2]
    return {
        'n_points_raised': len(pts),
        'n_reference_points': len(gt['points']),
        'matched': len(matched),
        'recall': round(len(matched) / len(gt['points']), 3),
        'consensus_matched': f"{sum(1 for i in cons if i in matched)}/{len(cons)}",
        'unmatched_raised': len(pts) - len(matched),
        'missed_ids': ','.join(gt['points'][i]['id'] for i in range(len(gt['points'])) if i not in matched),
    }


# -------------------------------------------------------------- T3-refs
def grade_t3refs(rec, adj):
    gt = {i['id']: i for i in load('data/t3/refs_input.json')['items']}
    got = {c.get('id'): c for c in (rec.get('conversions') or []) if isinstance(c, dict)}
    ok = part = 0
    detail = []
    for rid, spec in gt.items():
        c = got.get(rid)
        if not c:
            detail.append(f'{rid}:absent'); continue
        text = astext(c.get('converted')) + ' ' + astext(c.get('note'))
        n = norm(text)
        ch = spec['checks']
        fails = []
        for k in ('journal', 'volume', 'pages', 'year', 'doi_url'):
            if k in ch and norm(ch[k]) not in n:
                fails.append(k)
        for s in ch.get('must_contain', []):
            if norm(s) not in n:
                fails.append(f'missing:{s}')
        for s in ch.get('must_not_contain', []):
            if norm(s) in n:
                fails.append(f'present:{s}')
        if 'must_contain_any' in ch and not any(norm(s) in n for s in ch['must_contain_any']):
            fails.append('missing:any-of-expected')
        if not fails:
            ok += 1
        else:
            if len(fails) <= 1:
                part += 1
            detail.append(f'{rid}:{"/".join(fails)}')
            adj.write(json.dumps({'task': 't3refs', 'model': rec['model'], 'id': rid,
                                  'fails': fails, 'converted': c.get('converted'),
                                  'note': c.get('note')}, ensure_ascii=False) + '\n')
    return {'n_items': len(gt), 'fully_correct': ok, 'accuracy': round(ok / len(gt), 3),
            'one_defect_only': part, 'detail': ';'.join(detail)}


# ---------------------------------------------------------------- T3-ja
def astext(v):
    """Coerce a field to text: models sometimes return a list where the schema asks for
    a string (an answer split into bullets), which must not fail the whole cell."""
    if isinstance(v, list):
        return ' '.join(astext(x) for x in v)
    if isinstance(v, dict):
        return ' '.join(astext(x) for x in v.values())
    return str(v or '')


def grade_t3ja(rec, adj):
    gt = {i['id']: i for i in load('data/t3/ja_questions.json')['items']}
    got = {a.get('id'): a for a in (rec.get('answers') or []) if isinstance(a, dict)}
    ok = 0
    detail = []
    jp = re.compile(r'[぀-ヿ一-鿿]')
    n_jp = 0
    for qid, spec in gt.items():
        a = got.get(qid)
        if not a:
            detail.append(f'{qid}:absent'); continue
        ans = astext(a.get('answer'))
        n = norm(ans)
        if jp.search(ans):
            n_jp += 1
        fails = [k for k in spec.get('required', []) if norm(k) not in n]
        for key in ('required_any', 'required_any2', 'required_any3'):
            if key in spec and not any(norm(s) in n for s in spec[key]):
                fails.append(key)
        if fails:
            detail.append(f'{qid}:{"/".join(fails)}')
            adj.write(json.dumps({'task': 't3ja', 'model': rec['model'], 'id': qid,
                                  'fails': fails, 'answer': ans},
                                 ensure_ascii=False) + '\n')
        else:
            ok += 1
    return {'n_items': len(gt), 'correct': ok, 'accuracy': round(ok / len(gt), 3),
            'answered_in_japanese': f'{n_jp}/{len(gt)}', 'detail': ';'.join(detail)}


# ------------------------------------------------------------- T4-absent
def grade_t4abs(rec, adj):
    gt = {i['id']: i for i in load('data/t4/absent_rules.json')['items']}
    got = {a.get('id'): a for a in (rec.get('answers') or []) if isinstance(a, dict)}
    tp = fabricated = correct_refusal = missed = 0
    detail = []
    for qid, spec in gt.items():
        a = got.get(qid)
        if not a:
            detail.append(f'{qid}:absent'); continue
        claims = bool(a.get('in_document'))
        n = norm(a.get('answer', ''))
        if spec['answerable']:
            if claims and norm(spec['expected']).split()[0] in n:
                tp += 1
            else:
                missed += 1
                detail.append(f'{qid}:missed-answerable')
        else:
            if claims:
                fabricated += 1
                detail.append(f'{qid}:FABRICATED')
                adj.write(json.dumps({'task': 't4abs', 'model': rec['model'], 'id': qid,
                                      'answer': a.get('answer'), 'quote': a.get('quote')},
                                     ensure_ascii=False) + '\n')
            else:
                correct_refusal += 1
    n_ans = sum(1 for s in gt.values() if s['answerable'])
    n_abs = len(gt) - n_ans
    return {'answerable_correct': f'{tp}/{n_ans}', 'absent_correctly_refused': f'{correct_refusal}/{n_abs}',
            # one number per condition, so T4 can be plotted beside the other tasks:
            # answerable items answered and unanswerable items refused, out of all items
            'correct': tp + correct_refusal, 'n_items': len(gt),
            'fabricated': fabricated, 'fabrication_rate': round(fabricated / n_abs, 3),
            'detail': ';'.join(detail)}


# ------------------------------------------------------------ T4-phantom
def grade_t4ph(rec, adj):
    gt = {i['id']: i for i in load('data/t4/phantom_elements.json')['items']}
    got = {a.get('id'): a for a in (rec.get('answers') or []) if isinstance(a, dict)}
    ok = fab = 0
    detail = []
    for qid, spec in gt.items():
        a = got.get(qid)
        if not a:
            detail.append(f'{qid}:absent'); continue
        if a.get('exists') is False:
            ok += 1
        else:
            fab += 1
            detail.append(f'{qid}:FABRICATED')
            adj.write(json.dumps({'task': 't4ph', 'model': rec['model'], 'id': qid,
                                  'truth': spec['truth'], 'answer': a.get('answer')},
                                 ensure_ascii=False) + '\n')
    return {'n_items': len(gt), 'correctly_denied': ok, 'fabricated': fab,
            'fabrication_rate': round(fab / len(gt), 3), 'detail': ';'.join(detail)}


def anchored_match(items, texts):
    """Independent per-item matching with require_all gating.

    Built this way from the start: the T1 grader had to be rewritten twice because a
    greedy one-to-one assignment credited the wrong item when two items shared
    vocabulary, and because narrow anchors missed correct findings phrased differently.
    Each item is judged on its own, and every finding carrying an item's evidence counts
    as explained (a model may report the same defect twice).
    """
    hit, used = {}, set()
    for i, it in enumerate(items):
        need = [k.lower() for k in it.get('require_all', [])]
        anchors = it['anchor_any']
        for fi, txt in enumerate(texts):
            if any(k not in txt for k in need):
                continue
            if any(a.lower() in txt for a in anchors):
                hit.setdefault(i, fi)
                used.add(fi)
    return hit, used


def grade_t6(rec, adj):
    """MS-C carries ten seeded inconsistencies; MS-D is the corrected control."""
    gt = load('data/groundtruth/MS-C_groundtruth.json')
    probs = rec.get('problems') or []
    texts = [norm(f"{astext(p.get('location'))} {astext(p.get('problem'))}"
                  if isinstance(p, dict) else astext(p)) for p in probs]
    is_control = rec['task'] == 't6d'
    hit, used = anchored_match(gt['errors'], texts)
    _dh, dused = anchored_match(
        [{'anchor_any': d['match_keywords']} for d in gt['distractors']], texts)
    # off-task: formatting comments, which the prompt explicitly excludes
    off = {i for i, t in enumerate(texts)
           if any(k in t for k in ('dpi', 'tiff', '.bmp', 'vertical line', 'keyword',
                                   'running title', 'orcid', 'et al', 'doi'))}
    for i, p in enumerate(probs):
        if i not in used and i not in dused and i not in off:
            adj.write(json.dumps({'task': rec['task'], 'model': rec['model'],
                                  'unmatched': p}, ensure_ascii=False) + '\n')
    row = {'n_raised': len(probs), 'off_task_formatting': len(off),
           'flagged_distractors': len(dused - used),
           'unexplained': len(probs) - len(used | dused | off)}
    if is_control:
        row |= {'fp_on_consistent_control': len(probs) - len(off)}
    else:
        row |= {'n_errors': len(gt['errors']), 'detected': len(hit),
                'recall': round(len(hit) / len(gt['errors']), 3),
                'missed_ids': ','.join(gt['errors'][i]['id']
                                       for i in range(len(gt['errors'])) if i not in hit)}
    return row


def grade_t7(rec, adj):
    """The discriminating metric is false positives on the five category exemptions."""
    gt = load('data/groundtruth/MS-E_groundtruth.json')
    fnd = rec.get('findings') or []
    texts = [norm(f"{astext(f.get('location'))} {astext(f.get('rule'))} "
                  f"{astext(f.get('problem'))}" if isinstance(f, dict) else astext(f))
             for f in fnd]
    ex, exu = anchored_match(gt['exempt_items'], texts)
    ap, apu = anchored_match(gt['applicable_violations'], texts)
    for i, f in enumerate(fnd):
        if i not in exu and i not in apu:
            adj.write(json.dumps({'task': 't7', 'model': rec['model'], 'unmatched': f},
                                 ensure_ascii=False) + '\n')
    return {'n_findings': len(fnd),
            'exempt_falsely_flagged': len(ex), 'n_exempt': len(gt['exempt_items']),
            'flagged_exempt_ids': ','.join(gt['exempt_items'][i]['id'] for i in sorted(ex)),
            'applicable_detected': len(ap), 'n_applicable': len(gt['applicable_violations']),
            'applicable_recall': round(len(ap) / len(gt['applicable_violations']), 3),
            'missed_applicable': ','.join(gt['applicable_violations'][i]['id']
                                          for i in range(len(gt['applicable_violations'])) if i not in ap),
            'unexplained': len(fnd) - len(exu | apu)}


GRADERS = {'t2': grade_t2, 't6c': grade_t6, 't6d': grade_t6, 't7': grade_t7, 't3refs': grade_t3refs, 't3ja': grade_t3ja,
           't4abs': grade_t4abs, 't4ph': grade_t4ph}


def main():
    tasks = sys.argv[1:] or list(GRADERS)
    adj = open(ROOT / 'results/tasks_adjudicate.jsonl', 'a')
    for task in tasks:
        d = ROOT / 'results' / task
        rows = []
        for f in sorted(d.glob('*.json')) if d.exists() else []:
            rec = json.loads(f.read_text())
            m = rec.get('meta', {})
            row = {'model': rec['model'], 'seed': rec['seed'],
                   'error': rec.get('error') or rec.get('parse_error') or '',
                   'wall_s': m.get('wall_s'), 'in_tok': m.get('prompt_tokens'),
                   'out_tok': m.get('output_tokens'), 'prefill_tok_s': m.get('prefill_tok_s'),
                   'decode_tok_s': m.get('decode_tok_s'), 'ttft_s': m.get('ttft_s'),
                   'peak_vram_mib': m.get('peak_size_vram_mib')}
            try:
                row |= GRADERS[task](rec, adj)
            except Exception as e:
                row['grade_error'] = f'{type(e).__name__}: {e}'
            rows.append(row)
        if not rows:
            print(f'{task}: no results'); continue
        cols = list(dict.fromkeys(k for r in rows for k in r))
        with open(ROOT / f'results/{task}_summary.csv', 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
        print(f'== {task} ==')
        show = [c for c in cols if c != 'detail']
        print(' | '.join(f'{c:>12.12s}' for c in show))
        for r in rows:
            print(' | '.join(f'{str(r.get(c,""))!s:>12.12s}' for c in show))
        print()
    adj.close()


if __name__ == '__main__':
    main()
