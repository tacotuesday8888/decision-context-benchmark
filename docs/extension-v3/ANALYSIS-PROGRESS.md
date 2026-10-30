# Confirmation analysis checkpoint — incomplete study

Four configurations have finished: Jev first-party, Luna Decisions and Laya each
1,771 requests, plus ProtectAI's 761 candidate-only scans. Astra Responses, Luna
Responses and Nimble remain in flight. Do not treat this checkpoint as the completed
11,387-request experiment or use interim outcomes to change its settings.

The source-specific tables and per-example CSVs in `results/extension-v3/analysis`
are computed only for complete arms. An independent stdlib verifier rereads the
raw records and checks their hashes, class denominators, confusion counts, Brier
and log losses, reliability bins, paired point estimates and missing-response
bounds. All four pass. The crossed bootstrap has separate numerical unit tests;
this is not a claim of a second independent bootstrap implementation.

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

`figures/completed-arm-effects.png` and its SVG contain only the three completed
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
