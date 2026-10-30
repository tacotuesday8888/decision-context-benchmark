# Broader source audit — October 30, 2026

The Hugging Face connector works. This audit used live Hub cards, schemas and sample
rows, primary papers, and released GitHub files. Several complete JSONL releases were
also downloaded and counted as inert data. No model inference, dataset generation,
Docker execution, purchase or credential change was performed.

Our main gap is **good decisions to distinguish**, not another model name. We need
ordinary instructions that should be followed alongside attacks that plausibly relate
to the user's task, with the original task and policy available. Many large injection
datasets omit that context or contain only attacks. More rows alone do not fix this.

The machine-readable workstream audits contain inspected URLs, institutions where
verified, count units, construction methods, label meanings, access and license issues:

- `results/source-discovery/human-datasets.json`
- `results/source-discovery/agent-datasets.json`
- `results/source-discovery/benign-training.json`
- `results/source-discovery/priority-source-inspection.json`
- `results/source-discovery/catalog.json` and `catalog.csv` combine the inventory;
  aliases across workstreams are counted once. They are an inventory, not a larger
  experimental sample or a claim to have read every paper exhaustively.

The follow-up preparation goes beyond cards: **16,194 source records are now in a
canonical review format** under ignored raw-data paths. SPML contributes 16,012
policy/user rows with 840 exact policy strings (not yet independent policy families),
12,542 upstream positives and 3,470 negatives. One empty user prompt is retained and
flagged. AIB contributes 182 task/policy/conversation cases; 24 require multi-turn
review and 19 have unresolved multiple-tool-result candidate units. Source labels
remain separate from blank semantic gold. No split or inference eligibility is assigned.
See `results/source-discovery/review-preparation.json` for actual counts and receipts.

## What to use next

| Source | What was checked | Recommended use and remaining work |
|---|---|---|
| [SPML](https://huggingface.co/datasets/reshabhs/SPML_Chatbot_Prompt_Injection) | All 16,012 released CSV rows now parsed and prepared; 840 exact policy strings, explicit system policy/user text. Some subtle positive labels are ambiguous. | First adapter/label-audit candidate for a **policy-context** arm. Policies are not automatically legitimate user tasks. Split by policy/template and independently review labels before confirmation. |
| [AgentInjectionBench, ppradyoth](https://github.com/ppradyoth/AgentInjectionBench) | Pinned JSONL: 182 cases, 142 unsafe/40 safe; system policy, conversation, tools and execution criteria. | Practical task-aware pilot after exact message extraction and semantic review. Exclude reference assistant replies and gold metadata from inputs. Distinct from Sentinel Den's smaller fixtures already used in v4. |
| [INFUSE, Vanderbilt](https://github.com/judydnguyen/infuse) | Actual repository tree: 40 task instructions, 56 attack configurations. Task-1 instruction, benign surfaces, test script and attack config read. | Promising new coding-workflow source and possible later **prevention** study. Reconstruct exact observed file/tool text before detector use. Audit sandbox and verifiers before running anything. Not 2,240 independent tasks. |
| [Tensor Trust, Berkeley-led collaboration](https://github.com/HumanCompatibleAI/tensor-trust-data) | Actual curated files: 570 extraction and 776 hijacking robustness rows, plus 230 output-leak detection rows. | Human-written attack diversity with authentic game defenses. Separate game-policy study; historical attack success is not a benign/injection gold label. Data licensing remains unresolved; do not redistribute by borrowing the game-code license. |
| [PromptShield](https://huggingface.co/datasets/hendzh/PromptShield) | Full released JSON counted: 18,909 train, 1,000 validation, 23,516 test. Test has 23,359 unique exact prompts. | Large detector comparison or provenance-reconstruction lead. Released schema is prompt/label, not separate task/input. Do not invent a missing task. This dataset is distinct from Meta Prompt Guard and Azure Prompt Shields. |
| [NVIDIA agentic IPI](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1) | All 1,272 rows parsed, nine domains, 722 distinct injection texts; original request/policy/tools and attack are present. | Useful synthetic task-aware attack stress set. Successful-attack-selected training data, without a balanced benign arm. Preserve policies and distinguish constructed targets from observed current victim behavior. |
| [NotInject](https://huggingface.co/datasets/leolee99/NotInject) and [Boundary Pairs](https://github.com/3nesdeniz/agentic-prompt-injection-boundary-pairs) | NotInject: 339 existing model-generated benign trigger-word prompts. Boundary Pairs: 1,200 rows/600 pairs/50 synthetic workflows, released scenario-disjoint splits. | False-alarm and authorization stress arms. Neither automatically supplies a separate legitimate task. Boundary Pairs' source_context is a channel tag, not task text; author review is not independent adjudication. |
| [BrowseSafe++](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus) | Public card describes task-bearing matched clean/injected pages and multiple browser views. Actual files are gated and were not inspected. | Strong conceptual fit, conditional on access and terms review. Train is CC BY 4.0; hidden test inputs have evaluation-only restrictions. Do not train/tune on test, redistribute it, recover labels or submit publicly under this task. |

The inventory also covers InjecAgent, AgentDyn, ASB, WASP, WAInjectBench, R-Judge,
HackAPrompt, PINT, Gandalf, OR-Bench, deepset and PIGuard-related collections. These
have different purposes and are not interchangeable additional held-out datasets.

## Findings that change what we should do

1. **Do not accept a dataset card's pairing claim without checking the records.**
   NEXUS-IPI says injection only differs in context history. In both released versions,
   all 100 paired requests match, but **zero of 100 pairs have identical full planned
   steps**. In v1, only 80 pairs even share the complete first step. A monitor reading
   the plan can therefore use action differences, not just injected prose. These are
   potentially useful runtime-safety examples, not an isolated context manipulation.
   The downloadable bytes and pair checks are in priority-source-inspection.json.
2. **Count tasks, attempts and variants separately.** ASPI has 728 released pairs but
   only 92 distinct AgentDojo suite/task IDs and 2,184 attack variants. These are already
   related to exposed AgentDojo tasks. Tensor Trust's final paper reports 563,349 raw
   attempts and 294,680 distinct attacker inputs; the earlier version's 126,808 attempts
   is not the current count. Raw counts here remain paper-reported, not independently
   parsed archives.
3. **Release size can differ from paper size.** PINT advertises 4,314 benchmark inputs,
   but the inspected public repository releases an example YAML, not the full benchmark.
   WAInjectBench's 3,698 released detector rows have only id/text, so task instructions
   cannot be reconstructed from those files alone. HackAPrompt access is gated.
4. **Aggregates are not independent evidence.** PIGuard and Horizon collections reuse
   several upstream sources; R-Judge includes InjecAgent examples. Preserve original
   IDs and compare exact/near text and task groups against all prior project exposure.
5. **Published labels still need interpretation.** Attack success, unsafe proposed
   action, disallowed request, and injection presence are different outcomes. A failed
   attack remains an attack. An ordinary SQL request labeled as an injection without
   its policy is not reliable universal truth. Ambiguous cases need review, not silent
   relabeling or deletion after looking at model predictions.

## Machinery and reproduction

`python3 scripts/source_discovery/inspect_priority_sources.py` downloads public files
and parses their data without executing source code. The report records revisions,
URLs, byte sizes and SHA-256 receipts. Downloads stay under ignored
`data/raw/source-discovery/`; this audit does not redistribute the raw corpora.
Rerunning discovery can observe a newer upstream HEAD; use the recorded revision/URL
and digest when reproducing this audit or freezing a future collection.

`python3 scripts/source_discovery/catalog.py` rebuilds the combined inventory.
`python3 scripts/source_discovery/verify.py --require-cache` verifies local byte
receipts and independently reparses cached files to recompute count/pair findings.
Without that option it performs offline
structural checks suitable for CI, without claiming to re-download or re-review data.

`python3 scripts/source_discovery/prepare_review.py` reproduces the canonical review
records offline from the pinned cached sources, refusing to replace changed outputs.
Initial SPML acquisition uses `--download-spml`; AIB's pinned cache comes from the
priority inspection command. Focused safeguard tests check roles, exact text,
annotation/reference-answer exclusion, ambiguity and overwrite protection. Raw source
and review text stay ignored; only their count/hash summaries enter Git.

`python3 scripts/source_discovery/export_blinded_review.py` exports all 16,194 records
with opaque IDs, removes explicit source/annotation metadata, and creates a blank
reviewer CSV plus a separate mapping. Exact source text is preserved; corpus style or
canary strings can still reveal provenance, so this is annotation blinding rather
than guaranteed source blinding. Human review has not happened. All packet text,
answers and mappings remain ignored. Eight preparation/export tests pass.

The source search used Exa plus live Hugging Face and direct public-file inspection.
Search-result slots, actual datasets audited, complete files parsed, and sample/card
checks are different measures. The catalog records these separately. University
affiliation is provenance, not a quality score.

## Next experiment

Read METHODS-COMPARISON.md and CONTEXT-METHODS.md for what similar detector, agent and
context-classification papers imply for our design. Read NEXT-EXPERIMENT.md for the
executable handoff. First prepare original policy/task
and candidate text with blanks for unresolved semantic judgments. Review a blinded,
source-stratified set, group the partitions, check exposure, and freeze conditions.
Then run the existing models within the remaining independent provider caps. Existing
weak results and old frozen records stay intact. Constructed new datasets are allowed
if construction and labels are disclosed; they must not be presented as authentic
released tasks or independently human-reviewed data.

For the owner's latest two-chat workflow, use ASTRA-DESIGN-PROMPT.md: Astra researches
and improves the design/preparation, then writes the final `/goal` execution prompt
for a new GPT-6.1 Sol chat. NEXT-EXPERIMENT.md remains a proposed execution starting
point, not a constraint against a better justified design.
