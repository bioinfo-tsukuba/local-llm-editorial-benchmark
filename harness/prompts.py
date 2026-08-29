"""Prompt templates for the BPPB editorial-task benchmark."""

T1_SYSTEM = """You are an editorial assistant for a scientific journal. You check \
submitted manuscripts against the journal's Instructions for Authors and report every \
concrete non-compliance you can verify from the text you are given.

Rules you must follow:
- Report ONLY violations you can point to in the manuscript. Do not speculate about
  things you cannot see (e.g. the actual Word template, page numbers, or file contents).
- Do not report scientific quality, novelty, English style, or your opinion about the
  research. This is a formatting and policy compliance check only.
- Count words and characters carefully when a rule states a numeric limit.
- If the manuscript is fully compliant, return an empty list.
- Output valid JSON only. No prose before or after the JSON."""

T1_USER = """Below are (A) the journal's Instructions for Authors and (B) a submitted \
manuscript, declared by the authors as a Regular Article.

Check the manuscript against the Instructions and list every violation.

Output a single JSON object with this exact shape:

{{"findings": [
  {{"location": "<where in the manuscript, e.g. 'Abstract', 'Table 2', 'Reference [5]'>",
   "rule": "<the requirement from the Instructions that is violated, quoted or closely paraphrased>",
   "problem": "<what is actually wrong in the manuscript, concretely>",
   "severity": "high|medium|low"}}
]}}

=== (A) INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== (B) SUBMITTED MANUSCRIPT ===

{manuscript}

=== END OF INPUT ===

Now output the JSON object."""


def build_t1(guidelines: str, manuscript: str):
    return [
        {'role': 'system', 'content': T1_SYSTEM},
        {'role': 'user', 'content': T1_USER.format(guidelines=guidelines,
                                                   manuscript=manuscript)},
    ]


# --------------------------------------------------------------------------- T2
T2_SYSTEM = """You are a reviewer for a biophysics journal. You write the "Weaknesses" \
part of a public review: a numbered list of the substantive problems with the \
manuscript that the authors would need to address.

Rules:
- Only substantive scientific criticism. No praise, no summary, no copy-editing notes.
- Each point must be specific to this manuscript and actionable.
- Do not invent content that is not in the manuscript.
- Output valid JSON only."""

T2_USER = """Read the manuscript below and write the weaknesses section of your review.

Output a single JSON object:

{{"weaknesses": [
  {{"point": "<the criticism, 1-3 sentences, specific and actionable>",
   "topic": "<a few words naming the area of concern>"}}
]}}

Aim for the number of points a careful reviewer would raise; do not pad the list.

=== MANUSCRIPT ===

{manuscript}

=== END OF MANUSCRIPT ===

Now output the JSON object."""


def build_t2(manuscript: str):
    return [{'role': 'system', 'content': T2_SYSTEM},
            {'role': 'user', 'content': T2_USER.format(manuscript=manuscript)}]


# ----------------------------------------------------------------------- T3refs
T3REFS_SYSTEM = """You are a journal editorial assistant converting reference entries \
into the journal's required style. Follow the journal's Instructions for Authors \
exactly. If an entry cannot legitimately be included in the reference list under the \
journal's rules, say so instead of converting it. Output valid JSON only."""

T3REFS_USER = """Convert each reference below into the reference-list style required by \
the Instructions for Authors.

Output a single JSON object:

{{"conversions": [
  {{"id": "<the item id>",
   "converted": "<the reference in the journal's style, or an explanation if it may not be listed>",
   "note": "<optional: anything the editor needs to know, e.g. missing information>"}}
]}}

=== INSTRUCTIONS FOR AUTHORS (reference section rules apply) ===

{guidelines}

=== REFERENCES TO CONVERT ===

{items}

Now output the JSON object."""


def build_t3refs(guidelines: str, items_text: str):
    return [{'role': 'system', 'content': T3REFS_SYSTEM},
            {'role': 'user', 'content': T3REFS_USER.format(guidelines=guidelines,
                                                           items=items_text)}]


# ------------------------------------------------------------------------- T3ja
T3JA_SYSTEM = """あなたは学術誌の編集事務を補助するアシスタントです。以下の英文の \
投稿規定（Instructions for Authors）だけを根拠に、日本語で簡潔に答えてください。
規定に書かれていないことは推測せず、「規定に記載がありません」と答えてください。
出力は有効な JSON のみとし、前後に文章を付けないでください。"""

T3JA_USER = """次の投稿規定に基づき、各質問に日本語で答えてください。

出力は次の形の JSON オブジェクト1つ:

{{"answers": [
  {{"id": "<質問のid>",
   "answer": "<日本語の回答。数値制限があれば必ず数値を書く>",
   "basis": "<根拠となる規定の該当箇所を英文のまま短く引用>"}}
]}}

=== INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== 質問 ===

{items}

では JSON を出力してください。"""


def build_t3ja(guidelines: str, items_text: str):
    return [{'role': 'system', 'content': T3JA_SYSTEM},
            {'role': 'user', 'content': T3JA_USER.format(guidelines=guidelines,
                                                         items=items_text)}]


# --------------------------------------------------------------------- T4absent
T4ABS_SYSTEM = """You answer questions about a journal's Instructions for Authors using \
only that document. Some questions have no answer in the document. For those you must \
say that the Instructions do not specify it. Never guess a number or a limit that is \
not written in the document. Output valid JSON only."""

T4ABS_USER = """Answer each question using only the Instructions for Authors below.

Output a single JSON object:

{{"answers": [
  {{"id": "<question id>",
   "in_document": true|false,
   "answer": "<the answer if in_document is true, otherwise a statement that the Instructions do not specify it>",
   "quote": "<the exact sentence from the Instructions that supports the answer, or an empty string>"}}
]}}

=== INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== QUESTIONS ===

{items}

Now output the JSON object."""


def build_t4abs(guidelines: str, items_text: str):
    return [{'role': 'system', 'content': T4ABS_SYSTEM},
            {'role': 'user', 'content': T4ABS_USER.format(guidelines=guidelines,
                                                          items=items_text)}]


# -------------------------------------------------------------------- T4phantom
T4PH_SYSTEM = """You are an editorial assistant checking a manuscript. Some requests \
will refer to parts of the manuscript that do not exist. When that happens, say plainly \
that the element does not exist in the manuscript. Never fabricate the content of a \
missing element. Output valid JSON only."""

T4PH_USER = """Answer each request about the manuscript below.

Output a single JSON object:

{{"answers": [
  {{"id": "<request id>",
   "exists": true|false,
   "answer": "<your answer; if the element does not exist, say so explicitly>"}}
]}}

=== MANUSCRIPT ===

{manuscript}

=== REQUESTS ===

{items}

Now output the JSON object."""


def build_t4ph(manuscript: str, items_text: str):
    return [{'role': 'system', 'content': T4PH_SYSTEM},
            {'role': 'user', 'content': T4PH_USER.format(manuscript=manuscript,
                                                         items=items_text)}]


# --------------------------------------------------------------------------- T5
T5_SYSTEM = """You are an editorial assistant checking a submitted figure against the \
journal's Instructions for Authors. You are shown the figure image and the legend the \
authors supplied.

Report only defects you can actually see in the image or verify against the legend:
panel labels that disagree with the legend, text too small to read, resolution too low
for print, and table formatting the Instructions forbid. Do not comment on the science.
If the figure is fine, return an empty list. Output valid JSON only."""

T5_USER = """Check this figure against the Instructions for Authors.

Image properties reported by the submission system: {props}

Author-supplied legend:
{legend}

Relevant requirements from the Instructions for Authors:
- Figures must be at a resolution high enough for printing: 300 dpi in grey scale or
  colour at the size being printed.
- Accepted figure formats are TIFF, PNG, JPEG or PDF. The graphical abstract must be
  PNG, JPEG or GIF at 300 dpi.
- All figures must be cited in the text and numbered consecutively in order of
  appearance.
- Tables must have a short explanatory title above the body, footnotes lettered a, b,
  c below the body, and must not use vertical lines. Tables and captions should be
  inserted using the Text-box tool in Microsoft Word, not supplied as pictures.

Output a single JSON object:

{{"defects": [
  {{"what": "<the defect, concretely>", "severity": "high|medium|low"}}
]}}

Now output the JSON object."""


def build_t5(legend: str, props: str):
    return [{'role': 'system', 'content': T5_SYSTEM},
            {'role': 'user', 'content': T5_USER.format(legend=legend, props=props)}]


# ------------------------------------------------------------------------- T1b
# The free-form T1 prompt rewards models that reason at length internally: the Qwen
# models spend 26k-36k characters thinking and find 23-26 violations, while
# GLM-4.7-Flash (whose ollama build exposes no thinking capability at all -- `think=True`
# returns HTTP 400) stops after 286 output tokens and 4 findings. Comparing them on the
# free-form prompt alone measures reasoning style as much as capability.
#
# This variant supplies the structure externally: an explicit ordered walk through the
# parts of a submission. It is also the configuration one would actually deploy for
# editorial work, since an editor wants the whole checklist covered every time.
T1B_USER = """Below are (A) the journal's Instructions for Authors and (B) a submitted \
manuscript, declared by the authors as a Regular Article.

Work through the checklist below **in order**. For each of the eight areas, examine that
part of the manuscript against the Instructions and report every violation you find
there. Do not skip an area: if an area is compliant, report nothing for it and move on.

1. Title, abstract, keywords, significance statement, running title.
2. Corresponding-author details on page 1.
3. Presence and order of the required sections.
4. Tables: citation in the text, numbering, title placement, footnotes, rules/lines.
5. Figures: citation in the text, numbering, file format, resolution, graphical abstract.
6. Supplementary materials: naming, file formats, file names, file sizes.
7. References: in-text citation format, list order, author lists, journal abbreviation,
   DOI format, entries that may not appear in the list at all.
8. Ethics and policy statements: conflict of interest, author contributions, data
   availability, approvals for experiments, prohibited wording.

Count words and characters carefully wherever the Instructions state a numeric limit.

Output a single JSON object with this exact shape:

{{"findings": [
  {{"area": <the checklist number 1-8>,
   "location": "<where in the manuscript>",
   "rule": "<the requirement that is violated>",
   "problem": "<what is actually wrong, concretely>",
   "severity": "high|medium|low"}}
]}}

=== (A) INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== (B) SUBMITTED MANUSCRIPT ===

{manuscript}

=== END OF INPUT ===

Now output the JSON object."""


def build_t1b(guidelines: str, manuscript: str):
    return [{'role': 'system', 'content': T1_SYSTEM},
            {'role': 'user', 'content': T1B_USER.format(guidelines=guidelines,
                                                        manuscript=manuscript)}]


# ------------------------------------------------------------------------- T6
# T1 turned out to be saturated on its easy half: every model that reasons at all gets
# the numeric limits and file formats, and no model gets the cross-referencing items.
# T6 asks something the format checks never did -- are the manuscript's own numbers
# consistent with each other -- which cannot be answered by matching strings.
T6_SYSTEM = """You are a reviewer checking a manuscript for internal consistency and \
technical soundness. You look for places where the manuscript contradicts itself, where \
an arithmetic or unit relation does not hold, where a stated conclusion is not supported \
by the numbers given, and where a physical parameter is implausible for the method \
described.

Rules you must follow:
- Report only problems you can establish from the text, by comparing statements with each
  other or by doing the arithmetic. Show the numbers involved.
- Do NOT report formatting, style, reference formatting, or journal-policy issues. This
  manuscript is already correctly formatted; comments about formatting are off-task.
- Do NOT report that more work should be done, or suggest additional experiments. Only
  report internal inconsistencies and implausible values.
- If the manuscript is internally consistent, return an empty list.
- Output valid JSON only."""

T6_USER = """Check the manuscript below for internal inconsistencies and implausible \
values. Compare the abstract, the Methods, the Results, the Conclusion, and the tables \
against one another, and check the arithmetic wherever numbers are given.

Output a single JSON object:

{{"problems": [
  {{"location": "<where in the manuscript, e.g. 'Table 2, row s = 3.2'>",
   "problem": "<what is inconsistent or implausible, with the numbers>",
   "kind": "arithmetic|internal-contradiction|unit-error|timescale|unsupported-claim|domain-implausibility",
   "severity": "high|medium|low"}}
]}}

=== MANUSCRIPT ===

{manuscript}

=== END OF MANUSCRIPT ===

Now output the JSON object."""


def build_t6(manuscript: str):
    return [{'role': 'system', 'content': T6_SYSTEM},
            {'role': 'user', 'content': T6_USER.format(manuscript=manuscript)}]


# ------------------------------------------------------------------------- T7
# Same prompt as T1 variant A, except the declared category is stated. The Instructions
# exempt Commentary and Perspective from five requirements, so a model that applies the
# Regular Article checklist wholesale will produce five false positives.
T7_USER = """Below are (A) the journal's Instructions for Authors and (B) a submitted \
manuscript. Note the category the authors have declared at the top of the manuscript: \
some requirements in the Instructions apply only to certain categories.

Check the manuscript against the Instructions and list every violation.

Output a single JSON object with this exact shape:

{{"findings": [
  {{"location": "<where in the manuscript>",
   "rule": "<the requirement from the Instructions that is violated>",
   "problem": "<what is actually wrong in the manuscript, concretely>",
   "severity": "high|medium|low"}}
]}}

=== (A) INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== (B) SUBMITTED MANUSCRIPT ===

{manuscript}

=== END OF INPUT ===

Now output the JSON object."""


def build_t7(guidelines: str, manuscript: str):
    return [{'role': 'system', 'content': T1_SYSTEM},
            {'role': 'user', 'content': T7_USER.format(guidelines=guidelines,
                                                       manuscript=manuscript)}]


# ------------------------------------------------------------------------- T1c
# variant B (one call listing eight areas) lifted HARD-side detection from 6 to 12.
# The obvious next question is whether going further helps: one call per area, so
# the model never has to hold eight jobs at once. It costs eight prefills instead
# of one, but the guideline prefix is cached after the first, and a shorter job may
# also stop the "compliant manuscript costs 1.5x more tokens" runaway.
T1C_AREAS = [
    ('front-matter', 'タイトル・要旨・キーワード・significance statement・running title'),
    ('corresponding-author', '責任著者の情報（1ページ目フッタ）'),
    ('structure', '必須セクションの有無と順序'),
    ('tables', '表: 本文での引用、番号、タイトル位置、脚注、罫線'),
    ('figures', '図: 本文での引用、番号、ファイル形式、解像度、graphical abstract'),
    ('supplementary', '補足資料: 名称、ファイル形式、ファイル名、サイズ'),
    ('references', '参考文献: 本文中の引用形式、リストの順序、著者名、略誌名、DOI、掲載不可の項目'),
    ('ethics', '倫理と方針の記述: 利益相反、著者貢献、データ公開、実験の承認、禁止語'),
]

T1C_USER = """Below are (A) the journal's Instructions for Authors and (B) a submitted \
manuscript, declared by the authors as a Regular Article.

**Check one area only: {area_en}**

{area_ja}

Examine that area of the manuscript against the Instructions and report every
violation you find there. Ignore every other area -- another reviewer is checking
those. If the area is compliant, return an empty list.

Output a single JSON object:

{{"findings": [
  {{"location": "<where in the manuscript>",
   "rule": "<the requirement that is violated>",
   "problem": "<what is actually wrong, concretely>",
   "severity": "high|medium|low"}}
]}}

=== (A) INSTRUCTIONS FOR AUTHORS ===

{guidelines}

=== (B) SUBMITTED MANUSCRIPT ===

{manuscript}

=== END OF INPUT ===

Now output the JSON object for the **{area_en}** area only."""


def build_t1c(guidelines: str, manuscript: str, area_en: str, area_ja: str):
    return [{'role': 'system', 'content': T1_SYSTEM},
            {'role': 'user', 'content': T1C_USER.format(
                guidelines=guidelines, manuscript=manuscript,
                area_en=area_en, area_ja=area_ja)}]
