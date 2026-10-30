# Eligibility and estimand — draft before inference

The owner authorized defensible published labels with ambiguity quarantined. No
semantic labels will be supplied by an AI or simulated reviewer. The proposed
experiment measures agreement with independently preserved **published construction
labels**: intended task diversion versus the source's clean/control content. It does
not estimate independently adjudicated maliciousness or observed attack success.
Every result must retain that qualification. A detector disagreement is an error
relative to these labels, not proof of universally incorrect semantic judgment.

## Main source: published TaskTracker QA scenarios

Use only existing QA scenarios that reconstruct against publisher prompt hashes:
SQuAD question and its actual original paragraph; published injected AdvBench goal
and override wrapper for positive records; separately released original clean QA
record for negative records. Match question ID, paragraph bytes and original task
when selecting clean/attack pairs. Do not manufacture a clean counterpart, invent a
question or use generated model answers/verifier scores as labels.

The trusted task preserves the original request/data-separation prefix plus original
question. Candidate is the exact deterministically reconstructed full paragraph.
Normalized publisher hashes do not prove byte identity; source extraction rules,
byte hashes and original indices provide the additional trace. Clean hashes use the
publisher's cumulative raw UTF-8 convention. Preserve original spelling and broken
mid-word insertion; do not improve or repair published examples.

Exclude mixed/generated primary tasks, unsupported source reconstructions, missing
license/provenance, prior exposed task/document/template overlaps, unresolved label
meaning or incomplete context. CodeAlpaca-containing material remains audit-only
because of component restrictions. TaskTracker MIT, AdvBench MIT and SQuAD CC-BY-SA
component notices must accompany any selected redistributable examples.

The first draft split is rejected: 11 exact override wrappers crossed partitions.
The revised design reserves the entire new wrapper family for confirmation. Eight
articles supply 48 new clean development records; the 60 prior designated development
records supply existing attack checks. Confirmation currently has 408 task/content
pairs (204 matched questions/paragraphs) from 27 other articles. Source labels are
balanced; these are 27 article clusters, not 408 independent trials. Shared wrappers
within confirmation remain a dependence axis, not independent attack families.

## Supplemental static benign-instruction stress source

The community agent-injection-bench repository has 24 published synthetic fixtures.
Seventeen support the simple task/content comparison without missing additional
history or custom system policy: 14 intended attacks and three benign controls.
The latter include a legitimate imperative runbook and an article discussing
injection. Source code places each text in the declared document/page/tool surface;
retained tool cases must match their canned tool result exactly.

Exclude direct user instructions, multi-turn conversation hijacks, filename/metadata
surfaces outside our selected scope and cases requiring extra trusted system context.
Keep the source's whole eligible set in confirmation, with no templates used to tune
development. Its descriptions, family names, success criteria and labels must never
enter model requests. This is a small, disclosed community fixture stress test,
not production evidence or a precise false-alarm estimate. Do not pool it with QA
into a winner or imply its conceptual paper citations establish original-paper data.

## Quarantined / not adopted

Tau-bench private simulator goals are ineligible as actual user requests. Its actual
multi-turn histories are available, but user-only text can lose meanings supplied
by assistant clarification questions. A restrictive single-user-message catalog/
flight subset yields only six texts from four tasks; repeated trials do not fix
that coverage. We will not pad the run with it or silently summarize the dialogue.

NetInjectBench v1's data-availability section says artifacts will be released after
acceptance and supplies no repository. A bounded search found no usable release.
NTBench (Oct 23 preprint) warns that obvious unrelated attack goals do not test
near-target corruption. Its inspected paper/search did not supply usable released
records; no reconstructed example will be invented from a figure. These are real
limits on what the proposed distant-target QA study can establish.

## Remaining gates

These source decisions require the local validation and protocol freeze gates. Independently validate source
alignment, duplicate/template grouping, split boundaries and supplemental overlap;
complete the precision/budget analysis and exact settings/prompts; perform bounded
development checks before freezing confirmation. All five conditions must cover
every included confirmation pair. The specialist remains candidate-only.

## Scope of freshness

The exposure checks establish separation of the selected source documents/questions,
exact candidates and tested literal wrappers. They do not establish a new semantic
attack taxonomy: generic override and authority-claim tactics already appeared in
previous studies. A source-prefixed family identifier is not proof of an unseen tactic.
Fresh confirmation here means new task/document units and published constructions under
the already fixed detector policy, not novel attack mechanisms or model-pretraining
independence. The source-wide TaskTracker family remains a fixed conditioning factor.
