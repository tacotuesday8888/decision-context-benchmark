# Confirmation analysis checkpoint — incomplete study

Six configurations have finished: Jev first-party, Luna Decisions, Laya, Nimble
and Luna Responses each1,771 attempts, plus ProtectAI's761 candidate-only scans
(9,616 cells). Only Astra Responses remains in flight. Do not treat this checkpoint as the completed
11,387-request experiment or use interim outcomes to change its settings.

The source-specific tables and per-example CSVs in `results/extension-v3/analysis`
are computed only for complete arms. An independent stdlib verifier rereads the
raw records and checks their hashes, class denominators, confusion counts, Brier
and log losses, reliability bins, paired point estimates and missing-response
bounds. All six pass. A second explicit-multiplicity bootstrap implementation also
reconstructs all81 primary full-collection intervals for the five completed
contextual arms, including insufficient-group cases. It now also independently
reconstructs all324 preselected-control comparisons using frozen job membership.
The numerical check includes omitted intervals for insufficient groups.

The first inspected figure shows that authentic task information has different
associations across sources and models. Jev and Luna Decisions improve on parts of
InjecAgent, while Laya remains mixed and often worse with task context. No universal
context benefit or pooled winner follows. Many clean-source classification changes
are zero, which does not establish perfect probability quality or robustness to
unseen benign instructions. InjecAgent has attacks only; AgentDojo here has clean
fixtures only. Neither supports balanced accuracy on its own.

Jev has exact-0.5 abstentions, and Luna Decisions has at least one incomplete
classification pair; these are retained in explicit denominators. Native 0.5
forecasts still enter proper probability scoring. The figure labels complete versus
planned pairs. Reported intervals condition on existing fixtures/templates, with
few task groups; the three-task GitHub source is descriptive only. Controls and
reliability results are saved, but their final cross-model interpretation awaits
completion and verification of remaining arms.

`figures/completed-arm-effects.png` and its SVG contain only the five completed
contextual configurations. ProtectAI has no task contrast. The plot was visually
inspected for labels, interval direction, zero references and missing-group symbols.
It must be regenerated and inspected when more arms finish. No new PDF was built.

Reproduce a completed arm (from this repository, no inference or credentials):

```sh
.venv/bin/python scripts/extension_v3/analyze.py --config jev_firstparty
python3 scripts/extension_v3/verify_analysis.py --config jev_firstparty
.venv/bin/python scripts/extension_v3/figures.py
```

Analysis uses a settled per-arm ledger snapshot when available; this is a partial
accounting subset, not a final provider balance. Raw evidence remains immutable.
The ongoing full ledger includes other configurations and is not replaced by these
snapshots. A final all-provider closure audit remains required.

Initial representative error review is in `ERROR-REVIEW.md`. It also documents
that the narrow frozen credential-fixture regex does not remove prose/serialized
mentions; no claim of universally credential-free source fixtures is justified.
The source-construction labels remain unchanged.

Five source-specific fixed-bin reliability grids were generated. They retain
exact0.5 forecasts and bin counts; no fitted calibration or uncertainty bands are
claimed. High confidence on clean fixtures is visibly problematic for Laya and
ProtectAI. Attack-only and clean-only sources cannot identify population-wide
calibration. Marker counts and source-specific denominators remain explicit.

Nimble completed without operational failures or exact-0.5 ties. Independent
raw-record, request/response/accounting and 18 primary-interval checks passed.
Its task-weighted error changes on InjecAgent direct harm and stealing are
−19.07 and −34.44 percentage points (conditional 95% intervals [−35.79,−4.24]
and [−51.51,−18.00]). These attack-only sources cannot establish false-alarm
performance. Shopping error changes by +3.12 points [−3.95,+11.20]; the four
clean AgentDojo sources have zero classification changes. Probability losses
and controls remain separate; unchanged classifications do not imply unchanged
probabilities. All inherited-label, repeated-text and fixed-template limits apply.

Luna Responses has1,767 valid Boolean decisions and four retained transport failures,
with no invented scores. Its source-specific task-weighted error changes on
InjecAgent direct harm and stealing are−13.76 and−35.12 percentage points
(conditional95% intervals [−26.93,−3.35] and [−53.53,−17.26]). The direct-harm
miss rate still equals103/128 valid task responses (80.47%), versus122/129
candidate responses (94.57%). On stealing it changes68/143→21/143. Improvement
is not reliable prevention. Two shopping false alarms appear with task context,
versus none candidate-only. Clean-source valid decisions are correct relative to
inherited labels; two missing task responses mean zero complete-pair differences
cannot be read as perfect all-planned performance. Control intervals all include
zero and the subset is small. Final report still awaits Astra.
