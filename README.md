# A benchmark of locally hosted language models for journal editorial work

Manuscripts under review are confidential, so a journal that wants to use a
language model on them has to run it on hardware it controls. This repository
holds a benchmark that measures how far locally hosted, open-weight models get
on that work, and everything needed to reproduce the measurements.

**21 models from 3.3 to 81 GB, 8 editorial tasks, 283 measured conditions on a
single bench-top workstation, plus 44 measurements across two nodes.**

## What the measurements show

- Guideline compliance is reached at a useful level: the strongest single model
  detects **34 of 40** seeded violations with no false positives, and occupies
  **17 GB**.
- **Model size does not order quality on any task.** Rank correlation between
  weight size and score runs from −0.27 to +0.25; within one model family the
  65 GB member scores below its 13 GB sibling.
- A **deterministic checker** — regular expressions and arithmetic, no model —
  finds **30 of the same 40** in under 0.1 s. Combined with the 17 GB model the
  pipeline reaches **39 of 40**, so the marginal contribution of the language
  model is nine items.
- Peer-review support recovers **7 of 12** points that real reviewers raised.
  Useful as a check against oversight; not a reviewer.
- **Prompt structure moved scores further than any property of the hardware.**

## Layout

```
paper/manuscript.md         the manuscript
paper/technical-report.md   long form: methods, threats to validity, and the
                            seven corrections made during the study
paper/figures/              figures 1-6, 300 dpi
data/                       guidelines, 5 manuscripts with 63 verified seeded
                            defects, ground truth, figure stimuli, reviews
data/PROVENANCE.md          source, size and SHA-256 of every third-party input
results/                    283 conditions + summary CSVs + twonode/matrix.json
harness/                    runners, grader, ground-truth verifiers, the
                            deterministic control arm, figure generation
```

## Reproducing

Every tabulated number comes from `results/` via `harness/make_report.py` and
`harness/make_paper_figures.py`; none is transcribed by hand. Ground truth
passed 52 independent arithmetic checks before any model was scored — which is
how the *compliant control manuscript* was found not to be compliant.

Inference used ollama. Note that two runtime versions were in use and the
top-scoring model ran on the newer one; this is documented rather than hidden,
along with the other threats to validity, in `paper/technical-report.md`.

## Licence

Code and manuscript: MIT (`LICENSE`). Data created for this study: CC BY 4.0.
Third-party material is redistributed under its own terms — see `data/LICENSE`
and `data/PROVENANCE.md`.
