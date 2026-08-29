#!/usr/bin/env python3
"""Grade T1 results against the seeded ground truth.

Matching is a keyword-overlap prefilter, not a final verdict: every model finding that
does not match a seeded violation is written to results/t1_adjudicate.jsonl for human
review, because an unmatched finding may be a real violation that was not seeded
(a true positive we missed) rather than a hallucination.

Metrics per cell:
  recall     = seeded violations detected / 40
  precision  = findings matched to a seeded violation / all findings   (MS-A only)
  fp_rate    = findings on the compliant control MS-B (should be 0)
"""
import json, pathlib, re, sys, csv, collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
GT = json.loads((ROOT / 'data/groundtruth/MS-A_groundtruth.json').read_text())
RES = ROOT / 'results' / 't1'

MIN_HITS = 2          # keywords needed to call it a match
DISTINCTIVE = 10      # a single keyword this long counts as a match on its own


def norm(s):
    return re.sub(r'\s+', ' ', (s or '')).lower()


def finding_text(f):
    """Only the model's own claim is matched: 'location' and 'problem'.

    The 'rule' field is the journal's wording, which mentions neighbouring concepts and
    produces spurious matches (e.g. the rule about the corresponding author names both
    the postal address and the ORCID iD, so quoting it alone would look like a finding
    about both).
    """
    if isinstance(f, dict):
        return norm(' | '.join(str(f.get(k, '')) for k in ('location', 'problem')))
    return norm(str(f))


def hits(kws, txt):
    return [k for k in kws if k.lower() in txt]


def match(gt_items, findings):
    """Decide, independently for each ground-truth item, whether any finding reports it.

    Each item carries `anchor_any`: wording specific enough that a finding about a
    neighbouring issue cannot be credited to it. An item counts as detected when a
    finding contains one of its anchors AND either that anchor is long/specific on its
    own or the finding also contains a supporting keyword.

    Judging each item independently (rather than assigning findings to items one-to-one)
    avoids two errors that a greedy assignment makes: crediting the wrong item when two
    items share vocabulary, and undercounting models that bundle several related defects
    into a single finding.
    """
    texts = [finding_text(f) for f in findings]
    pairs, used_f = {}, set()
    for gi, v in enumerate(gt_items):
        anchors = v.get('anchor_any') or v['match_keywords']
        need = [k.lower() for k in v.get('require_all', [])]
        best = None
        for fi, txt in enumerate(texts):
            if any(k not in txt for k in need):
                continue
            a = [k for k in anchors if k.lower() in txt]
            if not a:
                continue
            sup = hits(v['match_keywords'], txt)
            if max(len(k) for k in a) >= 12 or len(sup) >= 1:
                score = len(a) + len(sup)
                if best is None or score > best[0]:
                    best = (score, fi, a + sup)
        if best:
            pairs[gi] = (best[1], best[2])
        # every finding carrying this item's evidence is 'explained', not just the best
        # one: a model may report the same defect from two angles, and calling the
        # duplicate a hallucination would be wrong.
        for fi, txt in enumerate(texts):
            if any(k not in txt for k in need):
                continue
            a = [k for k in anchors if k.lower() in txt]
            if a and (max(len(k) for k in a) >= 12 or hits(v['match_keywords'], txt)):
                used_f.add(fi)
    return pairs, used_f


def main():
    rows = []
    adj = open(ROOT / 'results/t1_adjudicate.jsonl', 'w')
    cells = sorted(RES.glob('*.json')) + sorted((ROOT / 'results' / 't1c').glob('*.json'))
    for f in cells:
        r = json.loads(f.read_text())
        fnd = r.get('findings') or []
        m = r.get('meta', {})
        row = {
            'model': r['model'], 'manuscript': r['manuscript'], 'seed': r['seed'],
            'num_ctx': r.get('num_ctx'), 'num_predict': r.get('num_predict'),
            'variant': r.get('variant', 'a'), 'think': r.get('think'),
            'error': r.get('error') or r.get('parse_error') or '',
            'n_findings': len(fnd),
            'prompt_tokens': m.get('prompt_tokens'), 'output_tokens': m.get('output_tokens'),
            'wall_s': m.get('wall_s'), 'prefill_tok_s': m.get('prefill_tok_s'),
            'decode_tok_s': m.get('decode_tok_s'), 'ttft_s': m.get('ttft_s'),
            'peak_vram_mib': m.get('peak_size_vram_mib'),
            'thinking_chars': r.get('thinking_chars'),
        }
        # Findings that are legitimate but were not seeded, or are defensible
        # over-strict readings. Classified out before counting false positives:
        # calling a correct observation a hallucination would misrepresent the model.
        art = GT.get('known_artifacts', [])
        art_hit = set()
        for i, fd in enumerate(fnd):
            t = finding_text(fd)
            for a in art:
                if any(k.lower() in t for k in a['match_keywords']):
                    art_hit.add(i)
        row['known_artifact_findings'] = len(art_hit)

        if r['manuscript'] == 'MS-A':
            pairs, used_f = match(GT['violations'], fnd)
            # index distractor matches in the ORIGINAL finding list so they can be
            # excluded from the review queue as well as counted
            _dp, _du = match(GT['distractors'], fnd)
            dused = {i for i in _du if i not in used_f}
            tp = len(pairs)
            row |= {
                'n_seeded': len(GT['violations']),
                'detected': tp,
                'recall': round(tp / len(GT['violations']), 3),
                'findings_matched': len(used_f),
                'unexplained_findings': len(fnd) - len(used_f | art_hit),
                'precision_prefilter': round(len(used_f | art_hit) / len(fnd), 3) if fnd else None,
                'flagged_distractors': len(dused),
                'missed_ids': ','.join(GT['violations'][gi]['id']
                                       for gi in range(len(GT['violations'])) if gi not in pairs),
            }
            # For the seven violations defined by a number (word counts, character
            # counts, dpi, MB), check whether the model stated the correct figure.
            # Detecting "the abstract is too long" but reporting 292 words instead of
            # 330 is a detection an editor cannot forward to the author as written.
            num_items = [(gi, v) for gi, v in enumerate(GT['violations']) if 'expected_number' in v]
            num_ok = sum(1 for gi, v in num_items
                         if gi in pairs and v['expected_number'].lower()
                         in finding_text(fnd[pairs[gi][0]]))
            row |= {
                'numeric_detected': sum(1 for gi, _ in num_items if gi in pairs),
                'numeric_correct': num_ok,
                'numeric_total': len(num_items),
            }
            for i, fd in enumerate(fnd):
                if i not in used_f and i not in art_hit and i not in dused:
                    adj.write(json.dumps({'cell': f.name, 'finding': fd}, ensure_ascii=False) + '\n')
        else:
            # the distractors survive into MS-B (they were never violations), so a
            # false positive there is often a distractor the model fell for
            _dp, dused = match(GT['distractors'], fnd)
            row |= {'fp_on_clean': len(fnd) - len(art_hit),
                    'flagged_distractors': len(dused)}
            for i, fd in enumerate(fnd):
                if i not in art_hit and i not in dused:
                    adj.write(json.dumps({'cell': f.name, 'finding': fd,
                                          'note': 'on compliant control'},
                                         ensure_ascii=False) + '\n')
        rows.append(row)
    adj.close()

    if not rows:
        print('no results yet'); return
    cols = sorted({k for r in rows for k in r}, key=lambda k: (
        ['model', 'manuscript', 'seed'].index(k) if k in ('model', 'manuscript', 'seed') else 9, k))
    with open(ROOT / 'results/t1_summary.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    hdr = ['model', 'manuscript', 'seed', 'detected', 'recall', 'n_findings',
           'unexplained_findings', 'flagged_distractors', 'fp_on_clean',
           'known_artifact_findings', 'wall_s', 'prefill_tok_s', 'decode_tok_s', 'peak_vram_mib']
    print(' | '.join(f'{h:>12.12s}' for h in hdr))
    for r in rows:
        print(' | '.join(f'{str(r.get(h, "")):>12.12s}' for h in hdr))
    print(f"\nadjudication queue: {sum(1 for _ in open(ROOT/'results/t1_adjudicate.jsonl'))} findings"
          f" -> results/t1_adjudicate.jsonl")


if __name__ == '__main__':
    main()
