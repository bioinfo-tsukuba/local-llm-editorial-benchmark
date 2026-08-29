# local-llm-editorial-benchmark

This repository will hold the benchmark, data, results and code accompanying

> **Benchmarking locally hosted language models for journal editorial work on a
> bench-top workstation**
> Haruka Ozaki (RIKEN / University of Tsukuba), with Claude Code

**It is intentionally empty until submission.**

## Why it is empty

The work is carried out in a separate repository. This one exists to be the
citable, stable artefact that accompanies the paper, so it is populated in one
step at submission time rather than tracking work in progress.

## How it gets populated

From the working repository:

```
python3 harness/make_public_release.py ../local-llm-editorial-benchmark
cd ../local-llm-editorial-benchmark && git add -A && git commit && git push
```

The assembler copies the manuscript, figures, data, results and harness, writes
the licences and a provenance file recording the source and SHA-256 of every
third-party input, and refuses to complete if a personal name reaches the tree.

**Do not commit anything here by hand.** The assembler clears the directory on
each run, so hand edits are lost and, worse, would not exist in the working
repository where the paper is actually maintained.
