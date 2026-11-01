# Stronger-control source audit — chronological research notes

Status note: the dated-stage statements below preserve the audit history. Preparation
and inference subsequently completed; final scope and findings are in PROTOCOL-v4.0.md
and RESULTS.md. Early zero-approval counts and prior accounting totals are not the
final experiment state. See execution-closure-v1.json for final accounting.

This new experiment starts from preserved v3 commit
`d929836982347374695a0d38797623f8276a1cd5`. All eight PR4 checks were observed
successful; the canonical checkout was clean. No historical result is changed.
Current accounting remains OpenAI $0.2896254 / TypeSafe $0.154397208 within the
independent $15/$20 caps. No new inference has run.

## Confirmed eligibility issues

The benign-instruction-bench collector at
`5d0ae7c438a7b01be2ac0a2e8bc943e45c8f851f` uses `task.instruction` as
`user_request` in `scripts/collect_taubench.py`. Upstream tau-bench revision
`59a200c6d575d595120f1cb70fea53cef0632f6b`, `tau_bench/envs/base.py:85`,
passes that field to the user simulator. `envs/user.py:55–79` places it in the
simulator's system prompt, tells the simulator to reveal information gradually,
and returns a generated utterance. Therefore the private instruction is not the
actual assistant-visible user message. Exclude the collector's task field from
our authentic-task condition; do not relabel it as an observed user request.

The same collector changes catalog names by appending existing InjecAgent attacks.
Its output labels encode differential replay, not independent semantic review or
attacker success. Creating new combinations ourselves is not authorized dataset
extraction. The repository releases scores, not the JSONL evaluation records.

Its `collect_agentdojo_pairs.py` separately computes ground-truth calls in clean
and injected environments, matches position/function but does not require equal
arguments, then assigns `int(text != clean_text)`. This does not alone establish
that a response contains an injection. We will not inherit that binary label as
semantic gold or treat such pairs as identical tool-call/environment comparisons.
All 17 InjecAgent tasks and their 62 instruction families were already exposed in
v3; unselected strings from those tasks are not fresh independent confirmation.

## A more defensible tau-bench pathway

The pinned upstream repository releases four historical trajectory files with
actual user messages, assistant tool-call IDs/arguments and returned tool messages.
The MIT license covers the repository (copyright Sierra, 2024). The adapter reads
JSON only and executes no source tools or model calls. It never uses the private
simulator goal as trusted task text.

Inventory: 13,896 linked response occurrences, 1,231 distinct candidate strings,
165 original task groups in airline/retail. Repeated trials and model trajectories
are grouped by original task. No examples are approved yet. No-attack trajectory
provenance is kept separate from semantic labels, which remain null. Dialogue
history, legitimate procedural instructions, shared product/flight documents,
state-changing calls and task-context policy still need inspection. The source's
reported task reward does not imply a benign-injection semantic label.

The exposure register includes all 1,243 prior prepared development/evaluation
rows, not only successful calls. Source-specific groups need cross-source mapping;
exact text hashes alone cannot certify freshness. Candidate records and private
source downloads remain ignored; tracked inventories contain provenance/hashes.

## Reproduction and remaining work

`python3 scripts/controls_v4/audit_sources.py` rebuilds the exposure register and
tau trajectory inventory from the pinned local checkout. Output approval counts
are deliberately zero until source/content/group checks are completed.

Next: inspect representative actual histories and tool schemas; quantify shared
entities/documents and prior group overlap; inspect further published attack traces
and human label provenance; build a review packet for unresolved cases. Then choose
eligible scope, split groups, precision and exact five-condition requests. No
confirmation freeze, provider access check or paid inference is justified yet.

## Verified TaskTracker reconstruction, not new generation

Pinned TaskTracker revision `b4fabe25504dc1d3f7c6fdf5e50d4bb209a152b0`
releases reconstruction indices and prompt hashes. We inspected its original and
recreation notebooks as text, rather than executing their environment-changing
cells. A deterministic adapter reconstructed 6,000 published SQuAD/CodeAlpaca QA
attacks, matching every normalized prompt hash. That component uses CC-BY-NC-4.0
CodeAlpaca data; its text remains ignored and it is not selected for inference.
The repository's Apache code license does not replace its separate data license.

A second path avoids that component: the released poisoned-validation indices
contain 3,120 SQuAD/AdvBench QA attacks (2,387 questions, 1,100 paragraphs, 35
Wikipedia articles, 520 existing attack prompts). All publisher-normalized prompt
hashes match. AdvBench's upstream LICENSE is MIT; SQuAD is CC-BY-SA-4.0; TaskTracker
is MIT. These are existing published constructions, not newly paired documents or
new attacks. Metadata, source bytes and license hashes are recorded. The original
question remains attached to its actual source paragraph. The inherited target is
intended task diversion, not successful exploitation or human semantic annotation.

The published clean-validation prefix supplies 1,204 QA records on 1,204 paragraphs
and 35 articles. All hashes verify. Its upstream verifier hashes the cumulative raw
UTF-8 prompt stream, whereas the poisoned verifier hashes each prompt with all
whitespace removed. We preserve that distinction; normalized agreement must not be
called byte-identical source recovery. No GPT verifier outputs are imported as labels.
The source's validation/test design is not our experiment partition.

The owner directed us to proceed with defensible published labels and quarantine
ambiguity rather than depend on arranging human reviewers. The 24-record policy
review packet remains blank and ignored; its manifest records original context,
construction labels and null semantic labels. It is not evidence of completed review.
Any eligible experiment must explicitly state its source-construction estimand and
exclude cases whose source alignment or label basis cannot support it.

## Shared content is substantive, but generic strings are not documents

The initial exact-string graph links 47/50 airline and 112/115 retail tasks, partly
through generic tool outputs. That is a diagnostic, not proof that every task must
be one split component. Restricting to catalog/flight search responses still links
76/80 retail tasks through 42 product-response texts and 23/34 airline search tasks
through 101 flight-result texts. These represent substantive sharing that a proposed
split must address. Generic acknowledgments and empty results will be distinguished
from documents/entities before eligibility; no arbitrary split will be justified by
counting repeated trial outputs as new independent tasks.

Representative inspected histories confirm the multi-turn issue: a flight search
follows destination/date, identity and cabin/payment preferences across three user
messages; a product lookup follows several exchange requests and fallback conditions.
Using only the opening utterance would omit authentic constraints. A deterministic
history policy must preserve original messages without model-written summaries or
private simulator instructions, and must avoid gold/outcome/previous predictions.
