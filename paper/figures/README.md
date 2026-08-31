# Figures: what each one is drawn from

Every figure is produced by `harness/make_paper_figures.py`, which reads `results/`
directly. No value is transcribed by hand. Regenerate all of them with:

```
python3 harness/make_paper_figures.py
```

Figures 1 and 2 are drawn rather than measured — they state the question and the task
design and carry no results, so they have no data dependency.

| Figure | Function | Reads | Key fields |
|---|---|---|---|
| 1 concept | `fig_concept` | — | drawn; the cell count is the only measured number |
| 2 tasks | `fig_tasks` | — | drawn |
| 3 detection tiles | `fig_tiles` | `harness/deterministic_check.py` output; `results/t1_summary.csv` | `missed_ids` per condition; the checker's own list of what it cannot decide |
| 4 size vs score | `fig2` | `results/{t1,t2,t3refs,t3ja,t5,t6c,t7,t8}_summary.csv` | `detected`, `matched`, `fully_correct`, `correct`, `applicable_detected`, `abbrev_correct`, plus `data/model_inventory.json` |
| 5 rank inversion | `fig2b` | the same eight summary CSVs | per-task rank derived from the same score fields |
| 6 prompt structure | `fig_prompt` | `results/t1_summary.csv` | `model`, `variant`, `manuscript`, `detected` |
| 7 prefill / decode | `fig3` | `results/t1/*.json`, `results/t2/*.json` | `meta.prompt_tokens`, `meta.output_tokens`, `meta.prefill_tok_s`, `meta.decode_tok_s` |
| 8 two nodes | `fig4` | `results/twonode/matrix.json` | `model`, `size_gib`, `nodes`, `prompt`, `metric`, `tok_s` |
| graphical abstract | `fig_graphical_abstract` | `DETERMINISTIC_BASELINE`; `results/t1_summary.csv` | drawn; carries the checker/model split |

Every file in this directory is a figure the paper cites.

Figure 3 is the only figure that shows the 40 violations individually rather than as a
count, which is what lets the text claim that the checker and the model fail on
different violations, and that one violation was found by the checker alone.

## Nothing quantitative lives in the plotting script

Values the figures need but cannot compute from `results/` are kept as data, not as
literals in the code:

| What | File | Used by |
|---|---|---|
| Model weight sizes and vision/tool capability | `data/model_inventory.json` | Figures 4, 5 |
| How the violations the checker cannot decide are classified, with the reason for each | `data/groundtruth/MS-A_unreachable_partition.json` | not plotted; verified by `check_claims.py` |
| Which of the 40 violations are EASY and which HARD, with the reason for each | `data/groundtruth/MS-A_difficulty.json` | Figure 6 centre |
| The pairs of conditions that define each change in Figure 6 right | `data/score_change_comparisons.json` | Figure 6 right |

The comparisons file names two measured conditions per row; the effect is the difference
between them, computed at plot time. It never stores an answer. The one exception is
`DETERMINISTIC_BASELINE` in the script, the score of `harness/deterministic_check.py`
run alone, which is named and sourced in a comment.

Externalising these caught two errors that had been in the manuscript. The difficulty
denominators were stated as 24 EASY and 16 HARD; recomputed from the recorded
classification they are 25 and 15, though every figure derived from the split — 20, 6,
19, 12 — was already correct. And the gain from decomposing the prompt was reported as
seven points, which is the figure for one model while the model shown alongside it gives
five.

## Renumbering

Figure numbers are part of the file names, so inserting a figure renames files. When
that happens, change the file name, the `savefig` call, the `![Figure n]` link, the
`**Figure n**` legend and every `(Figure n)` citation together, and check that
`Figure 4 was cited before Figure 3` in the Methods is left alone — that sentence
describes a defect inside the control manuscript, not a figure of this paper.
`check_manuscript.py` verifies that every figure is cited before it appears, that every
legend has a file and every file a legend.

## Order of operations after a re-run

```
python3 harness/grade_t1.py            # and grade_t5, grade_t8, grade_tasks
python3 harness/make_report.py         # regenerates results/*_summary.csv
python3 harness/make_paper_figures.py  # regenerates every figure
python3 harness/check_claims.py        # verifies the manuscript against results/
python3 harness/check_manuscript.py    # limits, references, figure wiring
```

## Table rules in the Word version

Markdown draws a rule between every row, which is not the convention the tables are
written for. In the submitted Word file each table takes three horizontal rules only:
above the header, below the header, and below the last row. No rule falls between data
rows. Table 3 groups two rows per model; the repeated model name is left blank on the
second row of each pair so the grouping survives without an internal rule.
