# Sizing a Local LLM Deployment for Journal Editorial Work: A Measurement Study on NVIDIA DGX Spark

**Author:** Haruka Ozaki (RIKEN)
**Date:** 2026-08-27
**Artifacts:** 283 task cells + 44 distributed-inference measurements; harness, data, and raw results accompany this document.

---

## Abstract

A scholarly journal's editorial board had ordered a 256 GB workstation to run local
large language models for editorial support — reviewer assistance and checking
manuscripts against submission guidelines — and had to re-decide after the vendor
could supply only 96 GB. The question "how much memory does this workload need?" is
normally answered by consulting model sizes. We answered it by measuring the workload.

We built an eight-task benchmark from a real journal's Instructions for Authors, five
purpose-written manuscripts carrying 63 verified ground-truth items, and the three
published peer reviews of a real preprint. We ran 21 models spanning 3.3–81 GB across
283 cells on a single NVIDIA DGX Spark (GB10, 119 GiB unified memory), plus 44
measurements on a two-node ConnectX-7 cluster. Coverage is defined per task by
capability: 17 models on the text tasks, the 11 vision-capable models on figure
checking, and the 15 tool-capable models on reference verification.

Four results bear on the sizing question. **(1)** The best single model on the
guideline-compliance task is one of the smallest tested: a 17 GB model detects 34 of 40
seeded violations with zero false positives, while no model above 60 GB exceeds it, and
within one model family the 65 GB member scores *below* its 13 GB sibling (15/40 vs
23/40). **(2)** A 220-line deterministic checker using only regular expressions and
arithmetic detects 30 of the same 40 violations with zero false positives in under
0.1 s and zero memory; combining it with the 17 GB model reaches 39/40, so the entire
LLM contribution above a scripted baseline is nine items. **(3)** Prompt structure
moves scores more than any hardware variable — decomposing the guidelines into eight
checklist areas is worth +7 points at no memory cost, versus +1 point for a 13.8 GiB
quantization increase — and for three models it determines whether the model completes
at all rather than degenerating into repetition. **(4)** Two nodes over RDMA make
prefill 1.6–1.8× faster independent of model size, but the workload is
decode-dominated (measured: 15.9 s prefill against 501.5 s decode in a single
compliance run), so the end-to-end saving is 1.1%; over TCP instead of RDMA, two nodes
run at 0.46× of one.

No task in the study reached its best observed score on a model larger than 38 GB, and
most reached it at or below 17 GB. We conclude that 96 GB is ample for this workload,
that the binding constraint on a purchase decision is memory *bandwidth* rather than
capacity, and — more generally — that the deterministic-checker baseline should be
established before any hardware is specified. We also report a correction: our own
initial conclusion that a two-node configuration was unsuited to this workload was
drawn from a published report whose transport and model choice we had not examined, and
measurement reversed it.

---

## 1. Introduction

### 1.1 The decision that prompted this study

The editorial board of a scholarly journal wanted to use local (self-hosted) language
models for two tasks: supporting peer review, and checking submitted manuscripts
against the journal's Instructions for Authors. Both involve unpublished manuscripts,
which is the usual reason to prefer local inference over a hosted API.

A 256 GB Apple Mac Studio had been ordered. The vendor could supply only 96 GB and
offered a refund of the difference. An alternative under discussion was two 128 GB
GB10-based workstations linked by a ConnectX-7 interconnect to yield 256 GB of
aggregate memory. The board needed to place an order within a week, constrained by a
grant's execution deadline.

The question as posed — 96 GB, 256 GB, or two nodes — is a hardware question. We
argue it cannot be answered as one. Memory capacity determines *which models fit*; it
does not determine *which models are needed*, and the second question is empirical.

### 1.2 Approach

Rather than compare specifications, we constructed the editorial tasks as a benchmark,
measured model quality on them, and derived the memory requirement from the models that
turned out to be sufficient. **Figure 1** sets out the motivating question and the study
design. This inverts the usual order (pick hardware, then see what
runs) and it is the reason the study's conclusion differs by more than an order of
magnitude from the initial premise.

Two design choices matter for interpreting everything below.

**Ground truth is constructed, not observed.** We wrote the manuscripts and seeded
known defects into them. This costs external validity — our seeded violations may not
match the distribution of real submissions — and buys exact recall measurement, which
a corpus of real submissions with unknown defect sets cannot provide. Section 8.1
treats this trade-off.

**A scripted baseline is measured, not assumed.** Discussions of LLM capability
routinely omit the question of what a short program achieves on the same input. We
implemented that program and measured it. It changed the study's conclusion.

### 1.3 Contributions

1. An eight-task benchmark for journal editorial work, built on a real journal's
   guidelines and the real published reviews of a real preprint, with 63 ground-truth
   items of which 52 are verified by independent arithmetic checks (§4, §5.4).
2. A 283-cell measurement of 21 models from 3.3 to 81 GB on unified-memory hardware,
   reporting quality, peak memory against context length, and cold-cache
   prefill/decode throughput (§6).
3. A quantified boundary between deterministic checking and LLM inference on the same
   task: 30/40 by code alone, 34/40 by the best LLM alone, 39/40 combined (§6.2).
4. A controlled comparison of prompt structure, quantization, model generation, and
   memory capacity as levers on the same metric, showing their effect sizes differ by
   nearly an order of magnitude in the opposite direction from the hardware intuition
   (§6.4).
5. A measurement of two-node RDMA inference isolating compute parallelism from memory
   relief, including a TCP control arm that inverts the result (§6.6), and a correction
   of our own earlier published claim (§9.2).

---

## 2. Related work and positioning

Benchmarks for scholarly-publishing tasks exist for peer-review generation and for
meta-review summarization, and general instruction-following suites cover
constraint-adherence in the abstract. Two gaps are relevant here, and both were
explicitly noted as open in the material we consulted before starting.

**No comparison against a deterministic baseline.** Guideline compliance is
substantially a matter of cross-referencing and counting — is every table cited, are
figures cited in order, is the abstract under the word limit. These are the operations
programs perform exactly. We are not aware of a study that measures what a scripted
checker achieves on the same items before attributing the remainder to model
capability. §6.2 supplies that comparison.

**No operating-point requirement for local deployment.** Published local-inference
results report throughput on standard models. They do not report the smallest
configuration that reaches a task's quality ceiling, which is precisely what a
purchasing decision needs. §6.1 and §7.1 supply that.

We also position this work against a specific published measurement: a report of
two-node GB10 inference over llama.cpp's RPC backend that measured 37.7 tok/s of prompt
processing on a 235B model. We initially cited that figure as evidence against the
two-node option. §6.6 shows the figure is an artifact of the transport (TCP) and the
model choice (too large for one node), and that the same topology over RDMA is 13×
faster.

---

## 3. System under test

### 3.1 Hardware

| Component | Specification |
|---|---|
| Machine | NVIDIA DGX Spark (hosts `spark-82f8`, `spark-a32c`) |
| SoC | NVIDIA GB10 Grace Blackwell, compute capability sm_121a |
| CPU | 20-core Arm: 10× Cortex-X925 + 10× Cortex-A725, aarch64, up to 4.00 GHz |
| Memory | 119 GiB unified (CPU/GPU shared); 114 GiB observed available |
| Memory bandwidth | ~273 GB/s |
| Swap | 15 GiB |
| Storage | 3.7 TB NVMe |
| Interconnect (two-node) | ConnectX-7, direct attach, RoCEv2 |

Because memory is unified, there is no discrete VRAM and `nvidia-smi` reports
`Memory-Usage: Not Supported`. All memory figures in this paper are therefore taken
from `free` and per-process RSS, not from `nvidia-smi`. This is a practical trap: the
conventional GPU-memory instrumentation silently reports nothing on this platform.

For context in the purchasing discussion, the comparison machines have ~819 GB/s
(Apple M3 Ultra) and ~1.2 TB/s (Apple M5 Ultra) of memory bandwidth, i.e. 3.0× and
4.4× the DGX Spark. This asymmetry — strong compute, mid-range bandwidth — is the
axis along which §6.5 and §7.2 interpret the speed results.

### 3.2 Software, and a runtime confound we did not control

| Component | Version |
|---|---|
| OS | Ubuntu 24.04.3 LTS, kernel 6.14.0-1013-nvidia |
| CUDA / driver | 13.0 / 580.95.05 |
| Inference runtime A | ollama 0.17.6, system service, port 11434 |
| Inference runtime B | ollama 0.32.15, user-space, port 11435 |
| Distributed inference | llama.cpp RPC backend (`rpc-server`, `llama-bench`) |

**Two runtime versions were in use, and this is a confound.** Runtime A was installed
as a system service and could not be upgraded without root, which was unavailable.
Two models released during the study period required a newer runtime, so a second
ollama instance was installed in user space with its own model store, deliberately
leaving the cells already measured against runtime A untouched.

The consequence is that **`qwen3.8:27b` and `gemma4` ran on ollama 0.32.15 while the
other 15 models ran on 0.17.6.** `qwen3.8:27b` is the top scorer on the primary task.
We cannot exclude that some part of its 3-point margin over the next model comes from
the runtime rather than the model. We consider a runtime-only explanation for a
3-point gap unlikely — the two runtimes implement the same sampling contract and we
pinned all sampling parameters (§5.3) — but it is unmeasured, and we flag it rather
than bury it. §8.5 lists it among threats to validity.

### 3.3 Model inventory

Seventeen models were measured. Sizes are the on-disk weight sizes reported by the
runtime; "active" gives active parameters per token for mixture-of-experts models,
which governs decode bandwidth demand.

| Model | Size | Architecture | Active | Vision | Tools | Runtime |
|---|---|---|---|---|---|---|
| `gemma3:4b` | 3.3 GB | dense | 4B | ✓ | — | A |
| `gemma4` | 9.6 GB | dense | — | ✓ | ✓ | **B** |
| `gpt-oss:20b` | 13 GB | MoE | — | — | ✓ | A |
| `mistral-small` | 14 GB | dense | — | — | ✓ | A |
| `magistral` | 14 GB | dense | — | — | ✓ | A |
| `qwen3.6:27b` | 17 GB | dense | 27B | ✓ | ✓ | A |
| **`qwen3.8:27b`** | **17 GB** | MoE, Q4_K_M, 27.3B total | — | ✓ | ✓ | **B** |
| `qwen3-vl:30b-a3b-instruct` | 19 GB | MoE | 3B | ✓ | ✓ | A |
| `qwen3:32b` | 20 GB | dense | 32B | — | ✓ | A |
| `qwen3.6:35b-a3b-q4_K_M` | 23 GB | MoE | 3B | ✓ | ✓ | A |
| `GLM-4.7-Flash` (Q8_0) | 31 GB | MoE | — | — | **—** | A |
| `qwen3.6:35b-a3b-q8_0` | 38 GB | MoE | 3B | ✓ | ✓ | A |
| `nemotron` | 42 GB | **dense** | 42B | — | ✓ | A |
| `command-r-plus` | 59 GB | dense | — | — | ✓ | A |
| `qwen3-vl:30b-a3b-instruct-bf16` | 62 GB | MoE | 3B | ✓ | ✓ | A |
| `gpt-oss:120b` | 65 GB | MoE | — | — | ✓ | A |
| `glm-4.5-air:q4` | 67 GB | MoE | 12B | — | **—** | A |
| `llama4:scout` | 67 GB | MoE | — | ✓ | ✓ | A |
| `qwen3.6:35b-a3b-bf16` | 71 GB | MoE | 3B | ✓ | ✓ | A |
| `qwen3.5:35b-a3b-bf16` | 71 GB | MoE | 3B | ✓ | ✓ | A |
| `qwen3.5:122b-a10b-q4_K_M` | 81 GB | MoE | 10B | ✓ | ✓ | A |

Capability is read from the runtime's own model metadata, not assumed. It defines the
population per task: 11 models carry a vision encoder and are eligible for T5; 15
support tool calling and are eligible for T8; the three that support neither
(`gemma3:4b`, `glm-4.5-air:q4`, `GLM-4.7-Flash`) are excluded from T8 by construction.
`gemma3:4b` and the two `qwen3-vl` variants participate only in T5, so the text tasks
have a population of 17.

Note that the top scorer is itself 4-bit quantized (Q4_K_M) and carries a CLIP
projector, i.e. it is a vision-capable model at 17 GB. §6.3 uses this.

Models excluded from measurement, with reasons, are listed in Appendix C. The short
version: Kimi K2 (1,026B, ~560 GB at 4-bit), DeepSeek V3/V3.1 (685B, ~375 GB), and
GLM-5.2 (744B, ~410 GB) do not fit even the two-node 238 GiB configuration, so the
256 GB option does not reach that class of model either.

---

## 4. Benchmark construction

### 4.1 Task suite

Eight tasks (**Figure 2**), chosen so that the two stated use cases are measured directly and so that
the axes along which models differ (input length, output length, reasoning depth,
vision, tool use) are separated rather than confounded.

| ID | Task | Input | Ground truth |
|---|---|---|---|
| T1 | Guideline compliance check | 12.3k tok | 40 seeded violations in MS-A; MS-B compliant control |
| T2 | Peer-review comment generation | 79.0k tok | 12 points extracted from 3 real published reviews |
| T3-refs | Reference format conversion | 7k tok | 8 items, mechanically decidable from the guidelines |
| T3-ja | Guideline queries in Japanese | 7k tok | 10 items |
| T4-abs | Hallucination resistance (guidelines) | 7k tok | 8 questions, 4 with no answer in the guidelines |
| T4-ph | Hallucination resistance (manuscript) | 12k tok | 5 questions about elements not present |
| T5 | Figure and table checking (vision) | 4 images | 5 seeded defects + 1 compliant figure |
| T6 | Scientific self-consistency | 12k tok | 10 internal contradictions in MS-C + 5 distractors |
| T7 | Category-conditional rules | 13k tok | MS-E as a Commentary: 5 exempt items, 8 applicable |
| T8 | Reference verification with tools | 7k tok | 8 items against Crossref and NLM Catalog |

T6 and T7 were added mid-study in response to a criticism we consider correct: the
initial suite over-represented problems that small models already solve. T4 was
saturated (a 13 GB model scored full marks) and T3-refs was flat (7 of 8 models scored
identically). A benchmark on which everything ties measures nothing. T6 requires
combining numbers stated in different sections and doing arithmetic; T7 requires
applying a rule set conditionally on the submission category, which is the failure mode
an editorial office actually fears (flagging a violation of a rule that does not apply).

### 4.2 Materials

**Guidelines.** The real Instructions for Authors of an active journal: 4,539 words,
7,604 tokens. Using real guidelines matters — a synthetic rule set would let us
control difficulty but would not reproduce the actual structure of such documents,
which mix hard numeric limits, formatting prescriptions, category-conditional
exemptions, and prose that is not a rule at all.

**Manuscripts.** Five manuscripts in the journal's subject area (biophysics), written
for this study.

| ID | Words | Content |
|---|---|---|
| MS-A | 2,832 | 40 seeded guideline violations, 6 distractors, 3 known artifacts |
| MS-B | 2,749 | MS-A with every violation corrected — compliant control |
| MS-C | ~2,800 | 10 scientific self-inconsistencies + 5 distractors |
| MS-D | ~2,800 | consistent control for MS-C |
| MS-E | ~2,900 | submitted as a Commentary: 5 rules exempt, 8 applicable |

The 40 violations in MS-A are classified into 24 **EASY** (decidable at a single
location, e.g. an abstract over the word limit) and 16 **HARD** (requiring two
locations to be reconciled, an ordering judgment, or noticing an absence, e.g. a table
that is never cited). This split is the paper's main analytical instrument: it
separates "reading a rule and applying it" from "cross-referencing and counting", and
the two behave very differently (§6.1, §6.2). The full taxonomy is Appendix A.

The distractors are text that superficially resembles a violation but is compliant.
The three "known artifacts" are places where writing a self-consistent manuscript
forced a construction that a strict reader could flag; they are excluded from both
numerator and denominator rather than being counted as either hits or false positives.

**Peer review reference.** For T2 we used a real preprint (eLife reviewed preprint
111064, arXiv:2512.17597) and its three published public reviews, from which we
extracted 12 distinct substantive points. One point is marked as consensus: reviewer 3
explicitly identifies it as "perhaps our biggest critique" — that the model is
described as mechanical while all mechanical aspects are abstracted away in simulation.
Tracking that point separately turned out to be informative (§6.1).

**Figure stimuli.** Four figures generated with matplotlib, carrying five defects (72 dpi
resolution, a table submitted as an image, panels labelled (c) where the legend says
(a)(b), unreadable axis labels, a table with vertical rules) plus one compliant figure.

Note on the T5 stimuli, because it limits what the task measures: the prompt
includes both the image (PNG, base64, via the runtime's `images` field) and the file
attributes a submission system would report (`FIG-2_low_resolution.png, PNG,
504x216 px, dpi=72, 14 KB`). This is realistic — a real pipeline has that metadata —
but it means only 3 of the 5 defects strictly require vision. **T5 scores must not be
read as pure visual capability.** §8.4 develops this.

**Tool-use items.** Eight reference-verification items for T8, checked against live
Crossref (`short-container-title`) and NLM Catalog (by ISSN) endpoints. The items
include a DOI that does not resolve, so that a model's willingness to fabricate a
plausible record can be distinguished from correct retrieval.

### 4.3 Tokenization

Prompt sizes must be measured, not estimated. We initially estimated tokens at 4
characters per token, a common rule of thumb. The measured ratio on this corpus is
**2.48 characters per token** — a 1.75× underestimate. The consequence was material:
the T2 prompt is 71,230 tokens, not the ~41,000 estimated, which exactly filled a
`num_ctx` of 65,536 and caused silent context truncation. All nine T2 cells measured
under that setting were discarded and re-run at `num_ctx=131072` (they are retained
under `results/_invalid_t2_ctx65k/`). Any study of long-context tasks that estimates
token counts from character counts risks this failure, and the runtime does not report
it as an error.

---

## 5. Method

### 5.1 Prompt variants

Three prompt structures were used for T1, holding the guidelines and manuscript
constant:

- **Variant A (free-form).** The guidelines and manuscript are supplied and the model
  is asked to list all violations. One call.
- **Variant B (checklist).** The guidelines are decomposed by us into eight areas
  (title page, abstract, body structure, figures/tables, references, ethics
  statements, formatting, submission metadata), and the eight areas are embedded in the
  prompt as an explicit checklist. One call.
- **Variant C (area-split).** As B, but one call per area — eight calls, results
  concatenated.

Variant B decomposes the guidelines but does not tell the model any of the answers; the
decomposition is derived from the guidelines' own section headings. We treat the
variant as a property of the harness, not of the model, which is why the same model
appears at several scores.

### 5.2 Output schema and grading inputs

Models are asked to return JSON: a list of findings, each with `location`, `problem`,
and `rule`. Only `location` and `problem` participate in matching. `rule` is excluded
deliberately: it quotes the journal's wording, which names neighbouring concepts, and
including it produces spurious matches — the rule about the corresponding author
mentions both the postal address and the ORCID iD, so a finding quoting that rule would
appear to be about both.

### 5.3 Inference parameters

| Parameter | Value |
|---|---|
| `temperature` | 0.0 |
| `seed` | 42, and 43/44 for repeat cells |
| `num_ctx` | 131072 (T1 also measured at 65536; T2 requires ≥131072) |
| `num_predict` | 24576 (T1), else unbounded |
| `think` | model-specific: `low`/`medium`/`high` where the model exposes reasoning effort |
| Model-default sampling | `top_p 0.95`, `top_k 20`, `min_p 0`, `repeat_penalty 1.0` remain as set by each model's own template |

Because `temperature` is 0, decoding is greedy and `top_p`/`top_k` are inert; we
nonetheless record them because they are part of the model's shipped configuration and
a reader reproducing this must not assume they were cleared.

**Observed determinism.** Greedy decoding was *nearly* but not exactly reproducible.
For `qwen3.6:35b-a3b-q8_0` variant A, seeds 42/43/44 produced identical output token
counts (10,895) and identical scores (26/40). For `qwen3.8:27b` variant B, seeds 42 and
43 produced byte-identical output (16,298 tokens) while seed 44 produced 15,793 tokens
— a different generation with the same score (34/40). `gpt-oss:120b` behaved likewise
(874, 874, 905 tokens; 11/40 throughout). We therefore report scores as stable across
seeds on this suite, while noting that the runtime is not bit-deterministic across
seeds at temperature 0, which is consistent with batch- or routing-dependent reduction
order in an MoE implementation. Three seeds is too few to characterize this; §8.3.

### 5.4 Ground-truth verification

Ground truth that is written by hand and then used to score models will propagate any
error it contains into every cell. We therefore verified it independently before use:
`verify_t6.py` performs 31 arithmetic checks on MS-C (each seeded inconsistency is
recomputed from the manuscript's own stated numbers) and `verify_t7.py` performs 21
checks on MS-E's exemption structure — 52 checks in total, all passing before any
model was scored.

This was not a formality. A model found a defect in **MS-B, the compliant control**:
Figure 4 was cited before Figure 3. The control was not compliant. It was corrected and
the affected cells re-run (superseded results retained under
`results/_stale_ms_b_v1/`). Had we trusted the control, every model that found this
would have been penalized with a false positive for being right.

### 5.5 Scoring

For each ground-truth item, matching decides independently whether *any* finding
reports it. Each item carries an `anchor_any` list — wording specific enough that a
finding about a neighbouring issue cannot be credited to it — and an optional
`require_all` list. An item counts as detected when some finding contains one of its
anchors, and either that anchor is distinctive on its own (≥10 characters) or the
finding also contains a supporting keyword (≥2 keyword hits).

Judging each item independently, rather than assigning findings to items one-to-one,
avoids two errors a greedy assignment makes: crediting the wrong item when two items
share vocabulary, and undercounting models that bundle several related defects into one
finding. We rewrote the grader twice before arriving at this: a greedy 1-to-1 matcher
mis-attributed findings, and an early anchor set was narrow enough to miss correctly
phrased findings.

**Keyword matching is a prefilter, not a verdict.** Every model finding that matches no
seeded violation is written to `results/t1_adjudicate.jsonl` for human review, because
an unmatched finding may be a real violation we failed to seed rather than a
hallucination — which is exactly how the MS-B defect surfaced. Reported false-positive
counts are post-adjudication.

Metrics per cell: recall (detected / 40), prefilter precision (matched findings / all
findings, MS-A only), and false positives on the compliant control MS-B, where the
correct output is an empty list.

### 5.6 Speed and memory measurement

Prefill throughput measured during task execution is contaminated by the runtime's
prompt cache: a second call sharing a prefix reports an inflated figure, and we
observed a meaningless 518,067 tok/s this way. Cold-cache speed measurements therefore
unload the model between runs and use inputs cut from real paper text.

Peak memory is sampled from `free` and process RSS during execution, reported as the
maximum over the run. Memory is measured at five context lengths (4k, 12k, 32k, 64k,
128k) to separate weight footprint from KV cache growth, which is architecture-dependent
by more than an order of magnitude (§6.3).

Two-node measurements use `llama-bench` against a `rpc-server` on the second host, with
transport selected by which address the server binds — the ConnectX-7 address for
RoCEv2/RDMA, the management LAN address for the TCP control arm. RDMA activation was
confirmed from the server log (`RDMA probed: RoCEv2`, `RDMA activated`) rather than
assumed.

### 5.7 Cell accounting

283 task cells are reported, distributed over twelve result sets: T1 78 (three prompt
variants over 17 models, MS-A and MS-B) and T1 variant C 10; T2 17; T3-refs 17 and
T3-ja 17; T4-abs 17 and T4-ph 17; T5 44 (11 vision-capable models x 4 figures); T6 17 on
MS-C and 17 on the MS-D control; T7 17; T8 15 (tool-capable models only). The 44
two-node measurements of §6.6 are counted separately, for 327 measurements in total.

**Coverage is defined by capability, not by convenience.** Presenting a 21 x 12 matrix
with holes would invite the reading that the gaps are omissions. They are not: figure
checking needs a vision encoder and reference verification needs tool-calling support,
and three models have neither. The populations are therefore stated per task — 17
models on the text tasks, 11 on T5, 15 on T8 — and every model that *could* run a task
did run it. The only exception is T1 variant C, run on 7 models rather than 17, because
it costs eight calls per cell; this is a deliberate limit and is flagged in §8.3.

An earlier version of this paper reported 260 cells, with T5 on 6 models and T8 on 13.
Those gaps were not capability limits but unrun cells, and the T5 gap mattered: the
models never run were exactly the 23–81 GB band, i.e. the range that decides whether
size helps on the one task where a size effect had been claimed. They were filled
before this version. §9.4 gives the consequence.

Ten further cells are excluded and retained under `results/_*/`, the directory name
giving the reason: 1 T2 cell invalidated by the tokenization error (§4.3), 3 superseded
by the MS-B correction (§5.4), 3 no-output cells from a model that produced nothing, 2
truncated by an output cap set too low, and 1 timeout. Note that the tokenization error
required re-running nine T2 cells, but only one invalidated cell was retained as
evidence. Excluding cells silently is how a benchmark flatters itself; the directory
names record what happened.

---

## 6. Results

### 6.1 T1: guideline compliance

Best score per model per prompt variant on MS-A (40 seeded violations), with false
positives on the compliant control MS-B.

| Model | Size | A | B | C | Best | FP (A) | FP (B) |
|---|---|---|---|---|---|---|---|
| **`qwen3.8:27b`** | **17 GB** | 32 | **34** | 33 | **34** | 2 | **0** |
| `qwen3.5:122b-a10b-q4_K_M` | 81 GB | 21 | 31 | — | 31 | — | 0 |
| `qwen3.6:35b-a3b-q8_0` | 38 GB | 26 | 31 | 27 | 31 | 0 | 0 |
| `qwen3.6:35b-a3b-q4_K_M` | 23 GB | 23 | 30 | 29 | 30 | 0 | 0 |
| `qwen3.6:27b` | 17 GB | 19 | 29 | — | 29 | 0 | 0 |
| `qwen3.6:35b-a3b-bf16` | 71 GB | 24 | 28 | 29 | 29 | 1 | 0 |
| `qwen3.5:35b-a3b-bf16` | 71 GB | 26 | — | — | 26 | — | — |
| `gpt-oss:20b` | 13 GB | 9 | — | **23** | 23 | 5 | — |
| `magistral` | 14 GB | 4 | 19 | 22 | 22 | 211 | 11 |
| `gemma4` | 9.6 GB | 11 | 18 | — | 18 | 1 | 0 |
| `glm-4.5-air:q4` | 67 GB | 17 | — | — | 17 | 228 | — |
| `mistral-small` | 14 GB | 3 | 17 | — | 17 | 0 | 309 |
| `gpt-oss:120b` | 65 GB | 14 | 15 | — | 15 | 1 | 1 |
| `nemotron` | 42 GB | 8 | 7 | — | 8 | 9 | 6 |
| `command-r-plus` | 59 GB | 1 | 7 | — | 7 | 0 | 30 |
| `GLM-4.7-Flash` Q8_0 | 31 GB | 3 | 2 | — | 3 | 1 | 1 |
| `llama4:scout` | 67 GB | 0 | 0 | — | 0 | 0 | 0 |

Four observations.

**Size does not order the results.** The top model is among the smallest tested. No
model above 60 GB exceeds 29/40. Within the `gpt-oss` family the 65 GB member scores
**below** its 13 GB sibling (15 vs 23), which cannot be explained by any capacity
argument. The three worst scores in the table belong to models of 31, 59, and 67 GB.

**Prompt structure is the largest single lever.** Every model measured under both A and
B improves under B, by +2 to +15 points. For `qwen3.6:35b-a3b-q8_0` the split by
difficulty class shows where the gain lands:

| Variant | EASY (24) | HARD (16) | Total | Wall time |
|---|---|---|---|---|
| A free-form | 20 | 6 | 26 | 345 s |
| **B checklist** | 19 | **12** | **31** | **311 s** |

The checklist doubles HARD detection and costs no time. This retired an earlier
conclusion of ours that cross-reference checking was beyond these models — the prompt
was at fault, not the capability. (§6.2 then shows the conclusion should have been
different again: those items belong in code.)

**False positives are near zero for competent models but catastrophic for degenerate
ones.** On the compliant control, the recommended configuration produces 0 findings.
Three models produce 200–300: `glm-4.5-air:q4` 228 and `magistral` 211 under variant A,
`mistral-small` 309 under variant B. These are not judgment errors but repetition
loops (§6.7).

**The most useful and the most harmful models are the same size.** At 14 GB,
`mistral-small` emits 309 false positives on a clean manuscript while at 13 GB
`gpt-oss:20b` emits 5 and at 17 GB `qwen3.8:27b` emits 0. Size predicts neither
quality nor safety.

### 6.2 The deterministic baseline, and where the boundary actually falls

We implemented `deterministic_check.py`: regular expressions and arithmetic only, no
parsing of Word or LaTeX (a production pipeline would have that), reading the same plain
text the models were given.

**Figure 3** shows the resulting decomposition.

| Method | Detected | False positives | Time | Memory |
|---|---|---|---|---|
| **Code only** | **30/40 (75%)** | **0** | **< 0.1 s** | **0** |
| `qwen3.8:27b` + checklist | 34/40 (85%) | 0 | 524 s | 17 GB |
| `qwen3.6 q8` + checklist | 31/40 (78%) | 0 | 311 s | 38 GB |
| `gpt-oss:20b` free-form | 9/40 | 5 | 34 s | 13 GB |
| **Code + `qwen3.8:27b`** | **39/40 (98%)** | **0** | 524 s | 17 GB |
| Code + `qwen3.8` + `qwen3.6 q8` | 40/40 (100%) | — | 835 s | 55 GB |

**The best LLM, using 5,000× the time and 17 GB of memory, adds four items to what a
short program finds.** And the program's coverage is concentrated exactly where the
models are weakest:

| Item | Cells that missed it | Code |
|---|---|---|
| V16 table numbering order | **27/27 (all)** | ✓ |
| V20 Figure 3 never cited | 25/27 | ✓ |
| V15 Table 1 never cited | 23/27 | ✓ |
| V21 figure citation order | 23/27 | ✓ |
| V31 bracketed citation format | 22/27 | ✓ |
| V39 missing animal-ethics approval | 23/27 | ✗ |

**No violation was detected by all 27 cells.** Every item was missed by some model. This
is direct evidence against a single-model design, independent of which model is chosen.

Partitioning the 10 items code cannot reach:

| Nature | Items | Belongs to |
|---|---|---|
| Semantic / contextual | V39, V40, V26, V08, V09 | **LLM** |
| Layout | V17, V18, V19 | code, given a Word/LaTeX parser |
| World knowledge | V37 (journal abbreviation) | **external tool** — solved, §6.4 |
| Structural | V14 | plausibly code |

**Only five of forty items genuinely require a language model.** The implied
architecture is a three-layer pipeline in which the LLM is the last and smallest layer,
and the correct order of work is: write the checker, connect the tools, then choose
hardware.

### 6.3 Memory

Peak resident memory (GiB) against context length. KV-cache growth is
architecture-dependent by a factor of ~14 across these models.

| Model | 4k | 32k | 64k | 128k | Δ(4k→128k) |
|---|---|---|---|---|---|
| **`qwen3.8:27b`** | **16.1** | — | — | **17.2** | **+1.1** |
| `gpt-oss:20b` | 13.1 | 13.9 | 14.7 | 16.4 | +3.2 |
| `qwen3.6 q4` | 24.4 | 25.2 | 26.2 | 28.2 | +3.8 |
| `GLM-4.7-Flash q8` | 30.0 | 32.8 | 35.9 | 42.3 | +12.3 |
| `qwen3.6 q8` | 38.2 | 39.0 | 40.0 | 42.0 | +3.8 |
| `gpt-oss:120b` | 61.3 | 62.3 | 63.5 | 66.0 | +4.7 |
| **`glm-4.5-air:q4`** | 64.9 | 80.4 | 98.0 | **113.8** | **+48.8** |
| `qwen3.6 bf16` | 68.6 | 69.4 | 70.4 | 72.4 | +3.8 |
| `qwen3.5:122b q4` | 80.4 | 81.3 | 82.3 | 84.8 | +4.4 |

The recommended model holds a 128k context for **+1.1 GiB** over 4k, a 32× context
increase. `glm-4.5-air:q4` requires +48.8 GiB for the same increase and is the only
model in the study that does not fit 96 GB at 128k — and it is also one of the three
that degenerate into repetition loops and the one that hallucinated missing references.
**The single model that would justify buying more than 96 GB is unusable for this
workload.**

Role-specific co-residency: the three recommended models together occupy ~76 GiB
resident, or 42 GiB if loaded sequentially. Both fit 96 GB.

### 6.4 Levers compared under matched conditions

This section corrects a confound in our own earlier analysis. We had reported
quantization q4→q8 as worth +8 points; that comparison was between q4's variant-A score
and q8's variant-B score, because only q8 had been measured under B. With the prompt
variant held fixed:

| Quantization | Weights | 128k peak | A | **B** |
|---|---|---|---|---|
| q4_K_M | 23 GB | 28.2 GiB | 23 | **30** |
| q8_0 | 38 GB | 42.0 GiB | 26 | **31** |
| bf16 | 71 GB | 72.4 GiB | 24 | — |

Under matched prompts, q4→q8 is worth **+1 point for +13.8 GiB**. Effect sizes for
every lever we can compare on the same metric:

| Lever | Memory cost | Effect |
|---|---|---|
| Quantization q4→q8 (matched prompt) | +13.8 GiB | **+1** |
| Quantization q8→bf16 (variant A) | +30.4 GiB | **−2** |
| **Prompt structure A→B** | **±0** | **+7** |
| **Model generation (3.6 q4 → 3.8, matched prompt)** | **−11 GiB** | **+4** |
| **Write the deterministic checker** | **±0** | **30/40 with no LLM** |
| **Attach an external tool (T8)** | ±0 | **0/4 → 4/4** |

Two of the three largest effects cost no memory, and one *reduces* it. The
journal-abbreviation item is the cleanest case: no model size and no prompt variant
solved `PNAS → Proc. Natl. Acad. Sci. U.S.A.` (7 of 8 models failed), because it is a
lookup, not an inference; giving a 13 GB model a Crossref/NLM tool took it to 4/4.

We flag the methodological point because we made the error: **comparing "best against
best" is invalid when the best scores were obtained under different conditions.** Fix
every axis but the one under study before tabulating.

### 6.5 Speed, and which phase dominates

Cold-cache throughput (model unloaded between runs, real paper text as input):

| Model | prefill @4k | @12k | @40k | decode |
|---|---|---|---|---|
| `gpt-oss:20b` | 3,106 | 3,208 | 2,326 | 55.6 |
| `qwen3.6 q4` | 1,367 | 1,387 | 1,263 | 54.7 |
| `qwen3.6 q8` | 1,235 | 1,263 | 1,166 | 43.3 |
| `gpt-oss:120b` | 1,178 | 1,190 | 1,052 | 39.9 |
| `qwen3.6 bf16` | 728 | 713 | 699 | 31.6 |
| `qwen3.5:122b q4` | 492 | 497 | 483 | 22.2 |
| `glm-4.5-air:q4` | 575 | 541 | 355 | 19.7 |

Effective bandwidth utilization exposes a quantization effect that is not about
capacity at all:

| Quantization | decode | Effective bandwidth | Fraction of 273 GB/s |
|---|---|---|---|
| q4_K_M | 50.2 | 75 GB/s | 28% |
| q8_0 | 35.7 | 107 GB/s | 39% |
| bf16 | 29.9 | 179 GB/s | 66% |

**Low-precision kernels here are dequantization-bound, not bandwidth-bound.** q4 reaches
28% of theoretical bandwidth, so "smaller quantization is proportionally faster" does
not hold, and a machine with 3–4× the bandwidth cannot realize that advantage at low
precision either.

**Which phase dominates is task-dependent, and the intuition is wrong for the primary
task** (**Figure 5**). Measured from the actual runs:

| Task | Input | Output | prefill | decode | decode share |
|---|---|---|---|---|---|
| **T1 compliance** (`qwen3.8`, B) | 12,272 | **16,298** | **15.9 s** | **501.5 s** | **97%** |
| T1 (`gpt-oss:120b`, A) | 11,527 | 24,576 | 10.0 s | 698.2 s | 99% |
| T1 (`qwen3.6 q8`, B) | 12,304 | 11,384 | 9.7 s | 277.0 s | 97% |
| T2 review (`qwen3.8`) | 78,983 | 3,505 | 127.2 s | 177.9 s | 58% |
| T2 review (`gpt-oss:20b`) | 70,904 | 581 | 31.3 s | 15.1 s | 33% |

On T1 the model **writes more than it reads** — 16,298 output tokens against 12,272
input — because it reasons at length before enumerating ~40 findings with quoted
evidence. Every model that produced a real answer on T1 spends 95–99% of its time in
decode. The cases where prefill dominates are the failures: `llama4:scout` (95 output
tokens, broken) and `GLM-4.7-Flash` (259 tokens, schema collapse). T2 inverts this, with
6× the input and a fifth of the output.

**The two use cases have opposite bottlenecks**, which is why a single hardware figure
of merit does not settle the purchase.

### 6.6 Two-node RDMA inference

44 measurements (**Figure 6**); principal conditions measured twice and agreeing
within 0.1–3.4%.

`glm-4.5-air:q4` (63.06 GiB, fits one node), prefill tok/s:

| Prompt | 1 node | 2 nodes RoCE | Ratio | 2 nodes TCP | Ratio | decode 1n | decode 2n |
|---|---|---|---|---|---|---|---|
| 4,096 | 686 | 1,125 | **1.64×** | — | — | 21.3 | 25.0 |
| 12,288 | 601 | 1,032 | **1.72×** | **274** | **0.46×** | 24.0 | 24.8 |
| 32,768 | 430 | 747 | **1.74×** | — | — | 21.7 | 24.8 |
| 71,230 | 282 | 500 | **1.77×** | **153** | **0.54×** | 21.7 | 24.9 |
| 131,072 | 186 | 323 | **1.74×** | — | — | 21.8 | 24.9 |

`qwen3.8:27b` (15.65 GiB, comfortably fits one node):

| Prompt | 1 node | 2 nodes | Ratio | decode 1n | decode 2n |
|---|---|---|---|---|---|
| 4,096 | 832 | 1,281 | **1.54×** | 12.23 | 12.46 |
| 12,288 | 797 | 1,314 | **1.65×** | 12.23 | 12.41 |
| 32,768 | 741 | 1,218 | **1.64×** | 12.20 | 12.38 |

**The speedup is compute, not memory relief.** A 15.65 GiB model — under no memory
pressure whatsoever on a 119 GiB node — still gains 1.6×. The ratio is flat across a
32× range of prompt length and across a 4× range of model size. Splitting buys parallel
compute.

**Decode is unaffected** (+1.2–1.5%; +15% only for the 63 GiB model). Prefill processes
all tokens in parallel and is compute-bound, so nodes help; decode is sequential and
bandwidth-bound per node, and adding a node does not raise any node's bandwidth.

**Without RDMA, two nodes are slower than one.** Over the management LAN, prefill falls
to 0.46–0.54× of a single node; the RoCE:TCP ratio is 3.8×. The interconnect is not an
accessory to this configuration, it is the entire value.

This resolves the discrepancy with the published 37.7 tok/s figure:

| | Published report | This study |
|---|---|---|
| Model | Qwen3-235B (**does not fit one node**) | GLM-4.5-Air (**fits one node**) |
| Transport | **TCP/IP** | **RoCEv2 / RDMA** |
| Prefill | 37.7 tok/s | **500 tok/s** |

The report's author states that TCP was a workaround because NVIDIA's native
multi-node stack is not ready on GB10. **The 37.7 tok/s was produced by the workaround,
not by the topology.**

**End-to-end effect on this workload.** T1's prefill is 15.9 s of a 524 s run. At 1.7×
that becomes 9.3 s, a saving of 6.6 s, or 1.1%.

| | 1 node | 2 nodes | Δ |
|---|---|---|---|
| Read one paper (71,230 tok) | 4.2 min | 2.4 min | −1.8 min |
| One compliance run (12k in / 16k out) | 524 s | ~518 s | **−6 s (1.1%)** |

Two nodes make the fast phase faster.

### 6.7 Failure modes

Three distinct failure modes appeared, none of which is captured by a score alone.

**Repetition collapse.** `glm-4.5-air:q4` emitted one finding 304 times;
`magistral` emitted a single finding 358 times on MS-A and 206 times on MS-B, hitting
the 24,576-token cap; the Qwen3.5 generation reached a 76.9% repetition rate, repeating
one DOI judgment 180 times. In every case the first few findings are correct and
degeneration begins at the point of an uncertain judgment (for `magistral`, "is this
postal address complete?"). Raising the token budget does not help; it produces more
copies.

**Prompt structure determines whether a model runs at all.** This is the finding we
consider most transferable:

| Model | Free-form | With structure |
|---|---|---|
| `magistral` | 358-fold loop, 37 min, 4/40 | checklist 19/40 in 156 s; area-split 22/40, **no loop** |
| `command-r-plus` | timeout | completes |
| `GLM-4.7-Flash` | 3/40 | **0/40** — schema collapse under the checklist |

Two models need structure to function; one is destroyed by it. **A model cannot be
assessed from one prompt format.** We reached the wrong conclusion about `magistral`
four times before measuring all three variants (§9.1).

**Long silence, then nothing.** The 17th T3-ja cell (`qwen3.5:122b-a10b-q4_K_M`) ran
for 1,217 s, consumed its full 24,576-token output budget, and returned an empty
response. This is the same degeneracy documented above rather than a new failure: the
model emitted reasoning tokens until the cap without producing an answer. It is
reported as a cell with no output rather than a zero score, because the two are
different claims about the model.

**Silent truncation and silent success.** Eight configuration items fail without
raising an error: `num_ctx` defaults to 4096 and silently truncates; raising reasoning
effort yields an empty string (observed for both `gpt-oss` models at `think=high`);
`ollama create` on a split GGUF imports only the first shard and reports success,
yielding a 106B model that claims 81.2B parameters and returns HTTP 500 on inference;
`ollama pull` returns exit status 0 on a 412 error. Every one of these produces output
that looks like a result.

### 6.8 Remaining tasks

| Task | Population | Best | Model | Notes |
|---|---|---|---|---|
| T2 review points | 17 | **7/12** | `gpt-oss:20b` (13 GB) | 81 GB model scores 4/12; the consensus "biggest critique" is found by 9 of 17 (see below) |
| T5 figures | **11 vision-capable** | **5/5** | `qwen3.6:27b` (17 GB), `qwen3.8:27b` (17 GB), `qwen3.6 q4` (23 GB), `qwen3.6 q8` (38 GB) | **nothing ≥62 GB reaches 5/5**; `llama4:scout` (67 GB) 3/5 with 3 false positives |
| T6 self-consistency | 17 | **7/10** | `qwen3.8:27b` (17 GB), `qwen3.5:122b` (81 GB) | family effect, not size: `gpt-oss:120b` 3/10 |
| T7 category rules | 17 | **8/8**, 0 false exempt | `qwen3.8:27b` (17 GB), `qwen3.6:27b`, `qwen3.6 bf16` (71 GB) | `gpt-oss:20b` 2/8 |
| T8 tool use | **15 tool-capable** | **4/4** | `gemma4` (9.6 GB), `gpt-oss:20b`, `magistral`, `qwen3.6 q4/q8/bf16`, `qwen3.5 bf16` | **`qwen3.8:27b` scores 0/4** |
| T3-refs | 17 | 6/8 | four models incl. `qwen3.8:27b` | flat across the field |
| T3-ja | 17 | 10/10 | `qwen3.6:27b`, `qwen3.6 q4` | `qwen3.8` 9/10; `qwen3.5:122b` returned an empty response after 1,217 s |
| T4 hallucination | 17 | saturated | 13 GB model at ceiling | 0 fabrications except `GLM-4.7-Flash` |

**Size does not order any task** (**Figure 4**). Spearman rank correlation between
weight size and normalised score, computed per task over every model that could run it:

| Task | n | *r*<sub>s</sub> |
|---|---|---|
| T1 guidelines | 17 | −0.04 |
| T2 review | 17 | −0.21 |
| T3 references | 17 | −0.27 |
| T3 Japanese | 17 | −0.20 |
| **T5 figures** | **11** | **+0.00** |
| T6 consistency | 17 | +0.25 |
| T7 category rules | 17 | +0.21 |
| T8 tool use | 15 | −0.23 |

Every coefficient lies between −0.27 and +0.25. We use rank correlation rather than
Pearson deliberately: on T5 the Pearson coefficient over the same 11 points is +0.41,
and that entire apparent effect comes from one model — `gemma3:4b`, a 3.3 GB model of
an older generation, scoring 1/5. Removing it turns Pearson *negative* (−0.31), and
restricting to models ≥17 GB gives −0.43. **A single old small model is enough to
manufacture a size effect in a Pearson coefficient**, which is worth stating because
that is the shape of the argument we are contesting.

Within T5, the four perfect scores are at 17, 17, 23 and 38 GB, and the four models at
62–81 GB score 3–4. Comparing the 17–38 GB band (mean 4.60, 4 of 5 at ceiling) against
the ≥62 GB band (mean 3.75, 0 of 4 at ceiling) gives a difference of +0.85 with an
exact permutation p of 0.135. **We therefore claim no size advantage, not a size
disadvantage**: the data are consistent with no effect, and n is too small to establish
the reverse.

**The consensus point is found more often than we previously reported.** Reviewer 3
marks one of the twelve points as "perhaps our biggest critique". Of the 17 models,
**9 identified it and 8 did not**; of the 8, four produced no usable output on T2 at
all, so among the 13 models that answered, 9 found it. An earlier version of this paper
stated that 8 of 9 models missed this point. That figure was correct when T2 had been
run on 9 models and is wrong now: the models added since are stronger, and the claim
inverted. The finding that survives is the aggregate one — the best model recovers 7 of
12 points — not a claim that models systematically miss the central critique.

Two further points deserve emphasis.

**Task rankings invert** (**Figure 4b**). `gpt-oss:20b` is 8th on T1 (23/40) and 1st on T2 (7/12);
`qwen3.6 q8` is 3rd on T1 and 11th on T2; `qwen3.8:27b` is 1st on T1 and scores 0/4 on
T8. **There is no single best model**, and a deployment must assign models to roles.

**No task required more than 38 GB to reach its best observed score.** T5 in
particular — the task most often invoked as an argument for capacity, since vision
models are expected to grow — has its ceiling reached by a 17 GB model, with a 9.6 GB
model one point behind and nothing above 60 GB reaching it at all.

---

## 7. Analysis

### 7.1 The memory requirement, derived

Working from the measurements rather than from model catalogues:

| Capability | Configuration | Peak memory |
|---|---|---|
| 39/40 compliance, 0 false positives | code + `qwen3.8:27b` @128k | **17.2 GiB** |
| Add review support | + `gpt-oss:20b` @128k | +16.4 GiB |
| Add figure checking and tool-based reference verification | + `qwen3.6 q8` @128k | +42.0 GiB |
| All three roles co-resident | | **~76 GiB** |
| All three roles, loaded sequentially | | **42 GiB** |

96 GB accommodates every configuration above. The workload's *minimum* viable
footprint is 17.2 GiB — 18% of a 96 GB machine, and about 1/15 of the 256 GB originally
specified.

What 256 GB uniquely enables, from the measurements: exactly one model in the study
(`glm-4.5-air:q4` at 113.8 GiB for 128k context), which loops and hallucinates; the
100–238 GB class of models, in which the study observed no quality advantage; and
training or fine-tuning, which we did not measure and where the capacity argument is
genuinely open. What 256 GB does not enable: the frontier-scale models (Kimi K2,
DeepSeek V3, GLM-5.2 at ~375–560 GB), which need 4–5 nodes.

### 7.2 Capacity, bandwidth, and compute are three different purchases

The measurements separate three quantities that a single "memory" number conflates.

- **Capacity** decides which models load. Measured requirement: 17.2–76 GiB.
- **Bandwidth** decides decode speed, which is 95–99% of the primary task's wall time.
  Effective utilization is 28% at q4 (§6.5), so bandwidth is not fully exploitable at
  low precision either.
- **Compute** decides prefill speed, which dominates the long-input review task and is
  the only quantity the second node improved (1.7×).

Buying capacity does not deliver the other two. On the specific machines in the
purchasing decision this becomes concrete: capacity and bandwidth are not independently
selectable, so a configuration with 1.33× the memory can carry 0.38× the bandwidth,
which for a decode-dominated workload is a net loss.

### 7.3 Why "bigger is better" fails here specifically

Three mechanisms, each visible in the data.

**Generation dominates scale.** Matched-prompt comparison gives +4 points for a
generation step that *reduces* memory by 11 GiB (§6.4). The trend in the observed model
population is capability rising while footprint falls; provisioning capacity as
future-proofing bets against the direction actually observed.

**Dense models are bandwidth-punished on this hardware.** `nemotron` (42 GB, dense)
decodes at 4.6 tok/s and `qwen3.6:27b` (dense) at 10.9, while a same-generation MoE with
3B active parameters reaches 43.3. At 273 GB/s, a dense model must stream all weights
per token. This is why the 42–67 GB band performs poorly here and why the result is
partly hardware-specific: on an 819 GB/s or 1.2 TB/s machine, the dense penalty shrinks.

**The tasks are not scale-limited.** The failures that persist across the whole field —
the cross-unit arithmetic error missed by 17 of 17 models, journal abbreviations failed
by 8 of 15 tool-capable models without a lookup — are not addressed by
capacity. Two are addressed by code and by a tool lookup; one appears to require a human
reviewer.

### 7.4 Implied architecture

```
[1] Deterministic checker      30/40   0 false positives, <0.1 s, 0 memory
[2] External tool lookups      journal abbreviations, DOI resolution — 4/4
[3] LLM, role-assigned         +9 items → 39/40, 17 GB
[4] Human                      cross-unit arithmetic, scientific judgment
```

The ordering is the practical result of this study. Layer 1 is the cheapest and largest
single contributor and requires no hardware decision at all; specifying hardware before
layer 1 exists means sizing a machine for work that need not be done on it.

---

## 8. Threats to validity

### 8.1 Manuscripts are synthetic

The five manuscripts are ours. Real submissions were unavailable. The gain is exact
ground truth; the cost is that our 40 seeded violations reflect our reading of the
guidelines, not the empirical distribution of violations in submissions. Absolute
recall numbers should therefore not be read as expected field performance. Comparative
statements — model against model, prompt against prompt, code against LLM — are
unaffected, since all conditions see identical inputs.

### 8.2 The review task rests on one preprint

T2's ground truth is 12 points from three reviews of a single paper in one subfield.
Whether `gpt-oss:20b`'s advantage on T2 generalizes is untested. The reference points
were extracted by us from review prose, which involves judgment about what constitutes a
distinct point.

### 8.3 Few repetitions, and one deliberately unfilled condition

Most cells are one seed. Repeats exist for four model/variant combinations at seeds
42/43/44 and showed identical scores, and principal two-node conditions were measured
twice (0.1–3.4% agreement). This supports stability but does not establish confidence
intervals, and we report no significance tests. Differences of 1–2 points in the T1
table should not be treated as separating models.

Separately, T1 variant C (one call per checklist area) was run on 7 of 17 models rather
than all of them, because it costs eight inference calls per cell. The variant-C column
of §6.1 is therefore not a complete comparison, and no claim in this paper rests on it
alone: the prompt-structure result is carried by variant A versus variant B, which was
run on every model that produced output.

### 8.4 T5 does not isolate vision

As constructed (§4.2), only 3 of 5 figure defects strictly require the image; the others
are derivable from supplied file metadata. T5 scores are therefore an upper bound on
visual capability, and the task should be read as "can the model check a figure given
what a submission system knows about it", not "can the model see".

The population is now all 11 vision-capable models, so the earlier objection — that the
absence of a size effect might reflect not having run the large models — no longer
applies. What remains is that T5 has 5 defects and one seed, which is why §6.8 reports
a permutation p rather than asserting a difference.

### 8.5 Two runtime versions

As stated in §3.2, the top-scoring model ran on ollama 0.32.15 while 15 of 17 models ran
on 0.17.6. The margin at stake is 3 points. This is uncontrolled.

### 8.6 Single runtime family, single machine class

All inference is via ollama (llama.cpp underneath). vLLM, SGLang, and TensorRT-LLM were
not used — the first two were not installed and the last has no SM121 GEMM kernels.
Throughput conclusions are specific to this stack. All results are from GB10 hardware;
the bandwidth-dependent conclusions (§7.3) would shift on higher-bandwidth machines,
and we say so explicitly wherever a conclusion depends on it.

### 8.7 Two-node measurements are microbenchmarks

§6.6 reports `llama-bench` prefill/decode throughput, not the T1–T8 suite executed
across two nodes. The "6 s saved per compliance run" figure is computed from measured
phase throughputs, not measured end to end. The TCP arm covers two prompt lengths.

### 8.8 Grading is keyword-anchored

Matching is lexical with human adjudication of unmatched findings (§5.5). A finding
that identifies the right defect in wording sharing no anchor would be scored as a miss
in the automated pass and would then have to be caught in adjudication. We rewrote the
grader twice for exactly this reason and cannot claim the current anchor sets are
complete.

---

## 9. Corrections made during this study

We record these because a reader assessing the reliability of the numbers above should
know where our judgment failed, and because two of them are methodological errors likely
to recur in similar studies.

### 9.1 Conclusions drawn from too few conditions

`magistral` was assessed and re-assessed five times. The successive claims were: "loops
forever and returns nothing" (its reasoning output was 0 characters); "writes normally
then truncates" (only the first three findings are normal); "degenerates from finding
four" (358 identical copies); "loops only in free-form, 19/40 under a checklist"; and
finally "improves monotonically with structure, 22/40 area-split, no loop". Stages 1–2
came from reading `done_reason` and character counts instead of the raw JSON. Stage 3
came from evaluating a model on one prompt format. **Long output is not evidence of
correct operation, and a single format is not a measurement.**

### 9.2 A conclusion imported from a published report without checking its conditions

Our initial report stated that the two-node ConnectX-7 configuration was unsuited to
this workload, citing 37.7 tok/s of prompt processing from a published measurement.
When a second node became available we measured 500 tok/s on the same topology. The
published figure was obtained over TCP with a model that does not fit one node; both
conditions were stated in the source and we did not examine them. **Citing someone
else's number as the basis of a conclusion requires reading their conditions, or
measuring it yourself.**

### 9.3 Comparing best-against-best across unmatched conditions

We reported quantization q4→q8 as +8 points; matched for prompt variant it is +1
(§6.4). The same error inflated our reported generation effect to +11 points, where the
matched figure is +4. In both cases the tabulated "best" scores had been obtained under
different prompt variants, so a prompt effect was being attributed to a hardware or
model variable.

### 9.4 An over-general claim about which tasks scale, and the experiment it prompted

We stated that figure checking was the only task where scale mattered, then that it was
one of two, then that neither survived. The correction has three stages and the last one
required new measurement.

The original claim rested on T5 spanning 1/5 at 3.3 GB to 5/5 at 38 GB — a range that
compares an old 4B model against a much larger recent one, so generation and size are
confounded. That much was visible in the existing data. What was *not* visible is that
T5 had been run on only 6 of the 11 vision-capable models, and the five never run were
`qwen3.6:27b` (17 GB), `qwen3.6 q4` (23 GB), `qwen3-vl bf16` (62 GB), `llama4:scout`
(67 GB), `qwen3.5 bf16` (71 GB) and `qwen3.5:122b` (81 GB) — **precisely the band that
decides the question.** A reviewer would have been entitled to say we had not measured
the large models on the one task where we claimed size did not help.

We ran them. The result strengthens the claim rather than weakening it: the ceiling is
reached at 17–38 GB and no model at 62–81 GB reaches it (§6.8). The same pass filled
T8 for the two tool-capable models that had been skipped; both scored 4/4, which does
not change any conclusion but removes another ragged edge.

Correct statement: **no task in this study demonstrates a requirement for capacity
above 38 GB, and none shows a rank correlation with size outside ±0.27.**

The general lesson is about which gaps are tolerable. A gap that follows from
capability — a text-only model cannot be scored on figures — is a fact about the
population and belongs in the paper as such. A gap that follows from not having run the
cell is a hole, and if it sits exactly where the contested claim lives, it will be read
as the reason for the claim.

### 9.5 A claim that expired when the population grew

We reported that the reviewer's self-identified "biggest critique" was missed by 8 of 9
models, and used it to argue that automated review misses what matters most. With the
population at 17 models the count is 9 found, 8 missed, and four of the eight produced
no output at all. **The claim did not become wrong through a measurement error; it
expired because the sample changed and we did not revisit it.** Any per-item claim
phrased as a fraction of the model population has this property, and we now state the
population inline wherever such a fraction appears.

### 9.6 A defective control

MS-B, the compliant control, contained a real violation (Figure 4 cited before Figure 3)
found by a model, not by us. Ground truth was wrong before models were. See §5.4.

### 9.7 Operational errors worth recording

A monitoring script gave false readings five times, in one case missing a 3 h 41 min
stall; editing a shell script while bash was executing it killed a job chain; a
`pgrep`-based wait matched our own inspection commands and blocked indefinitely; and
two bulk regex edits silently removed required code from the harness. None of these
affect the reported numbers, all of them cost time, and the mitigations are recorded in
the accompanying pitfalls document.

---

## 10. Practical recommendations

### 10.1 Build order

1. **Write the deterministic checker first.** 30/40 at zero marginal cost. This
   determines how much LLM capability is actually needed and can be done before any
   hardware exists.
2. **Attach external tools** for anything that is a lookup rather than an inference:
   journal abbreviations (NLM Catalog), DOI resolution (Crossref), retraction status.
   Measured 0/4 → 4/4.
3. **Add role-assigned models.** No single model wins across tasks.
4. **Keep the human on cross-unit arithmetic and scientific judgment.**

### 10.2 Configuration

| Role | Model | Setting | Measured |
|---|---|---|---|
| Compliance check | `qwen3.8:27b` (17 GB) | variant B checklist, `num_ctx` 131072 | 34/40 alone, 39/40 with code, 0 FP, 524 s |
| Review support | `gpt-oss:20b` (13 GB) | `think=low`, `num_ctx` 131072 | 7/12 reference points, 53 s |
| Figures, tool lookups | `qwen3.6 q8` (38 GB) | images via `images` field | 5/5 figures, 4/4 references |

Decompose guidelines into checklist areas in the prompt. Set `num_ctx` explicitly.
Verify `ollama pull` against `ollama list` rather than trusting exit status. Read the
pitfalls list before building, because all eight known failures are silent.

### 10.3 Hardware

**96 GB is sufficient** for every configuration measured, with the minimum viable
deployment at 17.2 GiB. The 256 GB premise exceeds the measured requirement by roughly
15×.

**Prefer bandwidth over capacity** when the two trade off. Decode is 95–99% of the
primary task and is bandwidth-bound; a configuration offering 1.33× capacity at 0.38×
bandwidth is a net loss for this workload.

**One node suffices.** Two nodes deliver a real, model-size-independent 1.7× on
prefill, but this workload's cost is in decode, and the end-to-end saving is 1.1%. If
the workload shifts toward high-input, low-output processing at volume, the second node
becomes worthwhile — and then **the RDMA interconnect is mandatory**, since the same
split over ordinary Ethernet runs at 0.46× of a single node.

**Unverified for other platforms.** These measurements are from Linux on GB10. On
macOS, the fraction of unified memory available to the GPU is capped by default and
adjustable (`iogpu.wired_limit_mb`); the ~76 GiB co-resident figure may approach that
limit, whereas sequential loading at 42 GiB has margin. Higher-bandwidth machines should
improve decode substantially relative to the figures here, while prefill may favour GB10.

---

## 11. Conclusion

The question "how much memory does local LLM editorial support need?" has a
counterintuitive answer on these measurements: 17.2 GiB for the highest-scoring
configuration, ~76 GiB for a three-role deployment, against a 256 GB premise. But the
more useful finding is that the question was mis-framed. Three quarters of the
guideline violations are found by a program with no model at all, and the largest
quality levers available — prompt structure, model generation, external tools — either
cost no memory or reduce it.

We also reversed one of our own published conclusions by measuring it. Two nodes over
RDMA are genuinely 1.7× faster at prefill; we had claimed otherwise on the strength of a
published figure whose transport we had not checked. The corrected conclusion happens to
support the same purchasing recommendation, but for a different and better reason: not
that two nodes fail to help, but that they help the phase this workload spends 3% of its
time in.

---

## Figures

| | |
|---|---|
| **Figure 1** | The motivating question and the study design. Carries no results. |
| **Figure 2** | What each of the eight tasks asks a model to do. Carries no results. |
| **Figure 3** | What each layer of the pipeline contributes to the 40 seeded violations. |
| **Figure 4** | Model size against normalised score, one panel per task, with the Spearman coefficient. |
| **Figure 4b** | Rank within task, model by model, showing that the ordering inverts. |
| **Figure 5** | Prefill and decode time for the two use cases. |
| **Figure 6** | Prefill throughput on one node, two nodes over RDMA, and two nodes over TCP. |

All figures are generated by `harness/make_paper_figures.py` from `results/`; no value
is transcribed by hand. Source files are in `BPPB-special-issue-paper/figures/` at
300 dpi.

## Appendix A — Violation taxonomy (MS-A)

40 violations, classified by whether a single location suffices to decide them.

**EASY (24)** — decidable at one location: abstract word count, title length, keyword
count, corresponding-author fields, section presence and order, reference count,
preprint declaration wording, funding statement presence, data-availability statement
presence, figure count, file-naming, line spacing, margin, font, page numbering,
citation style within a single reference, and similar.

**HARD (16)** — require reconciling two locations, judging order, or noticing an
absence: V14 preprint declaration in the wrong section; V15 Table 1 never cited;
V16 tables numbered out of order; V17 vertical rules in a table; V18 table title
placement; V19 footnote symbols; V20 Figure 3 never cited; V21 figures cited out of
order; V26 duplicated caption text; V31 bracketed citation format inconsistent with the
reference list; V37 journal abbreviation not in NLM form; V39 animal-ethics approval
absent though animal work is described; V40 conflict-of-interest statement incomplete
with respect to declared funding; V08/V09 completeness of required statements.

Excluded as known artifacts (3): constructions forced by writing a self-consistent
manuscript, counted in neither numerator nor denominator.
Distractors (6): compliant text resembling a violation.

## Appendix B — Task parameters

| Task | `num_ctx` | `num_predict` | Prompt tokens | Notes |
|---|---|---|---|---|
| T1 | 131072 (also 65536) | 24576 | 11.2–12.3k | 3 variants; `think` swept for `gpt-oss` |
| T2 | 131072 | unbounded | 70.3–79.0k | 65536 invalidated by silent truncation |
| T3-refs / T3-ja | 131072 | unbounded | ~7k | |
| T4-abs / T4-ph | 131072 | unbounded | 7k / 12k | |
| T5 | 131072 | unbounded | 4 images + metadata | per-figure calls |
| T6 | 131072 | unbounded | ~12k | MS-C and MS-D |
| T7 | 131072 | unbounded | ~13k | MS-E as Commentary |
| T8 | 131072 | unbounded | ~7k | live Crossref / NLM, real tool loop |

A guard in `run_tasks.py` skips and records any cell whose prompt exceeds the model's
context window, rather than letting the runtime truncate silently. `magistral`
(40,000) and `mistral-small` (32,768) cannot hold one paper (71,230 tokens) and are
therefore excluded from T2 by construction — **maximum context length is a third
selection axis alongside weight size and quality, and it is decidable from the model
card without measurement.**

## Appendix C — Models excluded, with reasons

**Do not fit, even on two nodes (238 GiB usable).** Parameter counts from safetensors
metadata; memory estimated at ~0.55 bytes/parameter for 4-bit.

| Model | Parameters | ~4-bit | 1 node | 2 nodes |
|---|---|---|---|---|
| Kimi K2 | 1,026 B | ~560 GB | ✗ | ✗ |
| DeepSeek V3 / V3.1 | 685 B | ~375 GB (404 GB as distributed) | ✗ | ✗ |
| GLM-5.2 | 744 B | ~410 GB | ✗ | ✗ |
| GLM-4.6 | 357 B | ~195 GB | ✗ | ✓ |

**Fit, but deprioritized.** `mistral-large` (73 GB) and `mixtral:8x22b` (79.5 GB): the
60 GB+ band scored 0–29/40 across seven measured models, so these were judged unlikely
to change the distribution. `deepseek-r1:70b` (42.5 GB): a reasoning-specialized model
that might have helped on T6, but Llama-70B-based and **dense**, so at 273 GB/s its
decode was extrapolated to be impractical (cf. `nemotron`, 42 GB dense, 4.6 tok/s).
This is an extrapolation, not a measurement, and is recorded as such.

## Appendix D — Reproduction

```
data/guidelines/     real Instructions for Authors (plain text)
data/manuscripts/    MS-A … MS-E
data/groundtruth/    per-task ground truth with anchor_any / require_all
data/figures/        4 matplotlib figures for T5
data/reviews/        3 published reviews for T2
data/t8/             8 reference items + Crossref truth
harness/run_t1.py    T1 variants A/B      harness/run_t1c.py  variant C
harness/run_tasks.py T2/T3/T4/T6/T7       harness/run_t5.py   vision
harness/run_t8.py    real tool-calling loop against Crossref/NLM
harness/deterministic_check.py   the scripted baseline (§6.2)
harness/grade_t1.py  scoring + adjudication output
harness/verify_t6.py harness/verify_t7.py  52 ground-truth checks (§5.4)
harness/twonode_*.sh two-node setup and measurement matrix
results/             283 cells + *_summary.csv; twonode/matrix.json (44 rows)
results/_*/          10 excluded cells, directory name gives the reason
```

All tabulated numbers are generated from `results/*.csv` by `harness/make_report.py`;
none are transcribed by hand. Ground truth passed 52 arithmetic checks before use.
Two-node transport is selected by the address `rpc-server` binds, and RDMA activation
was confirmed in the server log rather than assumed.

---

*Measurements: 2026-08-21 to 2026-08-26. The benchmark harness, datasets, raw results,
and a working log recording failed predictions accompany this document.*
