#!/usr/bin/env python3
"""Build docs/03-results.md from the graded summary CSVs.

Generating the tables from the CSVs rather than transcribing them keeps the report
honest: every number in the document traces back to a file in results/.
"""
import csv, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / 'results'

SHORT = {
    'gpt-oss:20b': 'gpt-oss 20b (13GB)',
    'gpt-oss:120b': 'gpt-oss 120b (65GB)',
    'qwen3.6:35b-a3b-q4_K_M': 'Qwen3.6 35B-A3B q4 (23GB)',
    'qwen3.6:35b-a3b-q8_0': 'Qwen3.6 35B-A3B q8 (38GB)',
    'qwen3.6:35b-a3b-bf16': 'Qwen3.6 35B-A3B bf16 (71GB)',
    'qwen3.5:35b-a3b-bf16': 'Qwen3.5 35B-A3B bf16 (71GB)',
    'qwen3.5:122b-a10b-q4_K_M': 'Qwen3.5 122B-A10B q4 (81GB)',
    'hf.co/ggml-org/GLM-4.7-Flash-GGUF:Q8_0': 'GLM-4.7-Flash q8 (31GB)',
    'hf.co/unsloth/GLM-4.5-Air-GGUF:UD-Q4_K_XL': 'GLM-4.5-Air q4 (~70GB)',
    'qwen3-vl:30b-a3b-instruct': 'Qwen3-VL 30B-A3B q4 (19GB)',
    'qwen3-vl:30b-a3b-instruct-bf16': 'Qwen3-VL 30B-A3B bf16 (62GB)',
    'gemma3:4b': 'Gemma3 4b (3.3GB)',
}
ORDER = list(SHORT)


def rows(name):
    p = R / name
    return list(csv.DictReader(p.open())) if p.exists() else []


def key(r):
    m = r.get('model', '')
    return (ORDER.index(m) if m in ORDER else 99, r.get('seed', ''))


def table(hdr, body):
    out = ['| ' + ' | '.join(hdr) + ' |', '|' + '|'.join('---' for _ in hdr) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in body]
    return '\n'.join(out)


def g(r, k, d='-'):
    v = r.get(k)
    return d if v in (None, '') else v


L = ['# 実測結果', '',
     '本ファイルは `harness/make_report.py` が `results/*.csv` から生成している。',
     '数値はすべて `results/` 配下の生データに対応する。', '']

# ---------------------------------------------------------------- T1
t1 = sorted(rows('t1_summary.csv'), key=key)
a = [r for r in t1 if r['manuscript'] == 'MS-A']
b = {(r['model'], r['seed']): r for r in t1 if r['manuscript'] == 'MS-B'}
if a:
    L += ['## T1 投稿規定整合性チェック', '',
          '仕込んだ違反 40件 / ディストラクタ 6件。`MS-B` は全違反を修正した適合版で、',
          'ここでの指摘は原則すべて偽陽性（既知アーティファクトを除く）。', '',
          '**測定条件について**: `num_ctx` は検証途中で 32768 から 65536 に、`num_predict` は',
          '16384 から 24576 に引き上げた（適合原稿でトークン上限に達して出力ゼロになるセルが',
          '出たため）。各セルの条件は下表に併記した。トークン上限に達したセルは',
          '`results/_truncated_16k/` に隔離して再測定しているので、検出数の比較は成立する。',
          'ただし**ピークメモリの列はセル間で比較しない**こと。文脈長でメモリが変わるため、',
          'メモリの議論には専用計測（後掲の文脈長ごとの表）を使う。', '']
    body = []
    for r in a:
        bb = b.get((r['model'], r['seed']), {})
        body.append([SHORT.get(r['model'], r['model']), r['seed'], g(r, 'num_ctx'),
                     f"{g(r,'detected')}/40", g(r, 'recall'), g(r, 'n_findings'),
                     g(r, 'unexplained_findings'), g(r, 'flagged_distractors'),
                     g(bb, 'fp_on_clean'), g(r, 'peak_vram_mib'),
                     g(r, 'prefill_tok_s'), g(r, 'decode_tok_s'), g(r, 'wall_s'),
                     g(r, 'error')])
    L += [table(['モデル', 'seed', 'num_ctx', '検出', 'recall', '指摘数', '説明不能な指摘',
                 'ディストラクタ誤検出', 'MS-B偽陽性', 'ピークVRAM(MiB)',
                 'prefill(tok/s)', 'decode(tok/s)', '所要(s)', 'エラー'], body), '']
    # per-area recall
    gt = json.loads((ROOT / 'data/groundtruth/MS-A_groundtruth.json').read_text())
    area = {v['id']: v['area'] for v in gt['violations']}
    areas = sorted(set(area.values()))
    body = []
    for r in a:
        missed = set(filter(None, (r.get('missed_ids') or '').split(',')))
        cells = []
        for ar in areas:
            ids = [i for i, x in area.items() if x == ar]
            cells.append(f'{len([i for i in ids if i not in missed])}/{len(ids)}')
        body.append([SHORT.get(r['model'], r['model']), r['seed']] + cells)
    L += ['### 領域別の検出内訳', '',
          table(['モデル', 'seed'] + areas, body), '']

# ---------------------------------------------------------- T2..T5
for name, title, cols in [
    ('t2_summary.csv', 'T2 査読コメント生成（実際の公開査読3名との論点一致）',
     [('matched', '一致'), ('recall', 'recall'), ('consensus_matched', '複数査読者が挙げた論点'),
      ('n_points_raised', '提示した論点数'), ('unmatched_raised', '参照外の論点'),
      ('in_tok', '入力tok'), ('prefill_tok_s', 'prefill'), ('decode_tok_s', 'decode'),
      ('wall_s', '所要(s)'), ('peak_vram_mib', 'VRAM(MiB)')]),
    ('t3refs_summary.csv', 'T3 参考文献の書式変換（8件）',
     [('fully_correct', '完全正解'), ('accuracy', '正解率'), ('one_defect_only', '欠陥1個のみ'),
      ('wall_s', '所要(s)')]),
    ('t3ja_summary.csv', 'T3 日本語での規定照会（10問）',
     [('correct', '正解'), ('accuracy', '正解率'), ('answered_in_japanese', '日本語で回答'),
      ('wall_s', '所要(s)')]),
    ('t4abs_summary.csv', 'T4 幻覚耐性: 規定に無いことを問う（8問中4問は答えが存在しない）',
     [('answerable_correct', '答えられる問'), ('absent_correctly_refused', '正しく「記載なし」'),
      ('fabricated', 'でっち上げ'), ('fabrication_rate', 'でっち上げ率'), ('wall_s', '所要(s)')]),
    ('t4ph_summary.csv', 'T4 幻覚耐性: 原稿に存在しない要素を問う（5問）',
     [('correctly_denied', '正しく否定'), ('fabricated', 'でっち上げ'),
      ('fabrication_rate', 'でっち上げ率'), ('wall_s', '所要(s)')]),
    ('t5_summary.csv', 'T5 図・表のチェック（VLM、欠陥5件＋適合図1枚）',
     [('detected', '検出'), ('recall', 'recall'), ('fp_on_compliant_figure', '適合図での偽陽性'),
      ('total_raised', '総指摘数'), ('wall_s_all_figures', '4図合計(s)')]),
]:
    rs = sorted(rows(name), key=key)
    if not rs:
        continue
    L += [f'## {title}', '',
          table(['モデル', 'seed'] + [h for _, h in cols] + ['エラー'],
                [[SHORT.get(r['model'], r['model']), r.get('seed', '')] +
                 [g(r, c) for c, _ in cols] + [g(r, 'error') or g(r, 'errors')] for r in rs]), '']

# ------------------------------------------------------- speed bench
sb = R / 'speed_bench.json'
if sb.exists():
    d = json.loads(sb.read_text())
    models = list(dict.fromkeys(x['model'] for x in d))
    tgts = sorted({x['target_tokens'] for x in d})
    L += ['## コールドキャッシュでの prefill / decode 実測', '',
          'タスク実行時の prefill 値はプロンプトキャッシュに汚染される（同一接頭部の',
          '2回目以降は見かけの速度が跳ね上がり、518,067 tok/s という無意味な値も観測された）。',
          'ここではモデルを毎回アンロードしてキャッシュを捨て、実物の論文本文を切り出した',
          '入力で測っている。40k tokens は論文1本に相当する。', '']
    body = []
    for m in models:
        row = [SHORT.get(m, m)]
        for t in tgts:
            hit = [x for x in d if x['model'] == m and x['target_tokens'] == t]
            if not hit or 'error' in hit[0]:
                row.append('err'); continue
            h = hit[0]
            row.append(f"{h['prefill_tok_s']:.0f} / {h['prefill_only_s']:.0f}s")
        for t in tgts[:1]:
            hit = [x for x in d if x['model'] == m and x['target_tokens'] == t]
            row.append(f"{hit[0]['decode_tok_s']:.1f}" if hit and 'error' not in hit[0] else 'err')
        body.append(row)
    L += [table(['モデル'] + [f'prefill @{t//1000}k (tok/s / 所要)' for t in tgts]
                + ['decode (tok/s)'], body), '']

# ------------------------------------------------------- KV footprint
kv = R / 'kv_footprint.json'
if kv.exists():
    d = json.loads(kv.read_text())
    models = list(dict.fromkeys(x['model'] for x in d))
    ctxs = sorted({x['num_ctx'] for x in d})
    body = []
    for m in models:
        row = [SHORT.get(m, m)]
        for c in ctxs:
            hit = [x for x in d if x['model'] == m and x['num_ctx'] == c]
            row.append(hit[0].get('size_vram_gib') or hit[0].get('error', '-')[:18] if hit else '-')
        body.append(row)
    L += ['## 文脈長ごとの実測メモリ占有（weights + KVキャッシュ、GiB）', '',
          '論文1本は約40k tokens（T2で使った実物のプレプリントで実測）なので、',
          '64k 文脈の列が実務上の目安になる。', '',
          table(['モデル'] + [f'{c//1024}k' for c in ctxs], body), '']

_out = ROOT / 'docs/03-results.md'
_out.parent.mkdir(parents=True, exist_ok=True)
_out.write_text('\n'.join(L) + '\n')
print('wrote docs/03-results.md', len(L), 'lines')
