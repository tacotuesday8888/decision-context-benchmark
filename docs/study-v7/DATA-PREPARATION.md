# V7 main-source preparation

This is source acquisition and offline grouping, not an experimental result. The
preparation code never invokes a model and never reads saved predictions or
accuracy calculations. Original publisher labels remain the primary reference.

The pinned BrowseSafe++ labeled training release is
`perplexity-ai/browsesafe-plus-plus` at
`3e9f4b3cef9295a1928ddfb33675eafd8bb68259`. Existing pinned metadata contains
59,000 pages in 29,500 pairs and 18,726 exact task/reference components. All 1,000
previously selected v6 components, including rejected examples, are historical
exclusions. Before full-text grouping, 15,579 English pairs in 10,177 remaining
metadata components form the fixed reserve pool. Both pages and the attack payload
must be declared exclusively English by the source; a clean arm has no payload.

Only complete `content_markdown`, the publisher's `benign_task`, and necessary
metadata are used. No screenshots, HTML, official test payloads, or unpublished test
labels are fetched. Source instructions are untrusted data. Raw text, source-view
diagnostics, and grouping edges stay under ignored `data/raw/study-v7/`.

Grouping starts with exact normalized task and injection-reference components
over the complete training metadata. It then closes task three-word Jaccard
similarity at 0.5 over that metadata and the historical source/preparation tasks.
Within the full English reserve, candidate similarity closes at 0.8. Historical
candidate screening uses the earlier conservative 0.5 threshold. Normalization is
NFKC plus case folding, followed by Unicode word tokenization. Near matching needs
at least five distinct three-word shingles; shorter normalized exact matches are
handled separately. The compact word-ID representation has no hash collisions,
and the exact prefix join is checked against both brute force and the earlier
project implementation.

Historical candidate inputs include all earlier source/preparation collections,
all 16,012 SPML source-discovery review prompts, AIB candidate tool messages, and
all 2,000 previously selected BrowseSafe++ source rows. Importantly, complete
Markdown is also acquired for **every member** of the metadata/task-closed
components touching previous selected pairs or historical task matches. This
includes unselected and rejected relatives; excluding their identifiers alone
would leave a document-overlap gap. Existing source text is reused and additional
training-column reads use a separate `browse-historical-relatives/` cache.

The 4,100 locked PromptShield validation/confirmation inputs are fixed first
and added as taskless candidate exclusion inputs at the 0.5 threshold. Their
receipt explicitly names the prepared checkout, rather than pretending they came
from the historical checkout. Entire main components touching any exclusion input
are excluded. The source labels and semantic-concern log are separate from these
technical/source-overlap decisions. The final external v3 source-input bytes are
identical to the v2 inputs used by the in-progress main closure; the before-lock
`results/study-v7/main-external-v3-equivalence.json` receipt checks both source
files and selection locks explicitly. No grouping or cohort changed for that
source-provenance update.

This document closure covers the full eligible English reserve and complete
historical/task-held components. It does **not** rule out longer paths through
unacquired non-English pages outside those components, semantic template
relationships, or overlap with private model-training data. Grouping reduces
dependence; it does not certify statistical independence or representativeness of
all webpages. Domain or generic boilerplate alone is not a grouping key.

Within each final eligible component, one complete source pair is chosen by frozen
hash rank. Component ranks allocate 200 development groups, followed by 3,000
confirmation groups when feasible. Separate purposes lock the shared 500-group
general subset, 100-group audit packet, repeats, and 50 development execution
groups before any outputs are available. The exact rank is
`SHA256(seed + NUL + source + NUL + purpose + NUL + canonical_id)`, with seed
`study-v7-plan-20261101` and UTF-8 encoding. Its implementation is in
`scripts/study_v7/main_data.py`.

The tracked `results/study-v7/main-selection.json` records actual attained counts,
source and output hashes, exclusion counts, edges by type, complete subset IDs,
and the immutable selection lock. It is produced only after grouping completes.
If the target is unattainable, the artifact says so; the request-plan assembler
must reject the full target instead of silently changing its denominator.

The completed preparation attained 200 development and 3,000 confirmation groups,
with one complete pair per group: 6,400 selected pages. The final usable pool has
9,853 fresh components. The historical/task-held components cover 7,654 pairs;
2,986 additional pairs were downloaded and the rest reused from existing source
text. There are 9,935 remaining language-ineligible pairs outside that held set.
No technically malformed reserve pair was found. Mechanical reference-binding
concerns were recorded for 1,167 reserve pairs and did not remove or relabel them.
These are preparation counts, not detector accuracy or audit findings.

The locked subsets contain 500 shared general-model groups, 100 audit groups,
100 native-repeat groups, 50 general-repeat groups nested within the general
subset, and 50 execution groups drawn from the 200 development groups. No
cross-source exact/near hit was found between the full English reserve and the
locked 4,100 external inputs under the stated screening rule. The main selection
lock is `a45c8ac045e14dcdb4e923f76a0929556ad59144747431c723e4760f7391ea39`.

Run `python -m scripts.study_v7.main_data --verify` to check existing local source
receipts, cohort/pair/partition hashes, nested subsets, and the fixed audit packet
without any network or model access. The independent final review also checks
selected main/external overlap.
