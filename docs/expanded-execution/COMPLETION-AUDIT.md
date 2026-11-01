# Research delivery audit — October 29, 2026

The intended expanded evaluations are complete. Detection and native forecast
quality differ by model and source; this does not establish attack prevention.
No additional inference, calibration fitting or threshold selection is required
for this frozen study. The original pilot and preparation are unchanged.

| Requirement | Current evidence |
| --- | --- |
| Finish prepared evaluations | `execution-audit.json`: 5,274/5,274 cells; 5,262 valid classifications, seven exact-0.5 abstentions, five operational failures. Six context-aware configurations each have 812 cells; Protect AI has 402 candidate scans and 445 forward windows. |
| Verify identities, usage and failures | Terminal audit reparses raw records, compares exact frozen requests, independently checks Nimble loaded digest/context, verifies Laya no-truncation records, links remote reservations, and checks the exact v2.3.3 continuation policy. One lost Astra attempt remains explicitly unknown with its zero-metered reservation. |
| Preserve collection and experimental safeguards | Frozen 402 evaluation/60 development collection; all 182 protected original pilot files verified. No generated examples, new gold labels, invented task context, evaluation tuning, or failed-cell replacement. |
| Paired source-specific analysis | `summary.json`, `forecast-summary.json`, `research-summary.json`, and `per-example.csv`; 97 classification strata and 67 native-score strata. Independent verification checks point estimates and cluster-bootstrap endpoints, common-score denominators, ties, selected errors and accounting. Boolean outputs never become fabricated probabilities. |
| Primary-source literature and citations | `LITERATURE-REVIEW.md`, `literature-source-receipts.json`, source-specific preparation notices and 12 manuscript references. Close prior work, public-data contamination, synthetic fixtures and label differences are explicit; no novelty claim. |
| Scientific figures and academic draft | Nine PNG/SVG figures, `paper/manuscript.md`, and the 11-page PDF. `paper/build-manifest.json` binds inputs and outputs; `paper-visual-review.json` records actual page/figure inspection. Document-versus-family interval selection was corrected before delivery. |
| Tests and integrity | 92 passing tests: execution 31, Laya 7, Nimble 7, preparation 18, original suite 29. Terminal execution audit, independent numerical gate, paper hash gate, preparation verifier and pilot verifier all passed. CI runs the terminal, numerical and paper gates too. |
| Reproducibility | `offline-reproduction.json`: all nine offline commands succeed in an isolated staged export; all 26 compared numerical/text/PNG/SVG/PDF artifacts are byte-identical. Credentials, weights and raw downloads are absent. Existing installed dependency runtimes were used; fresh package installation was not claimed. Tested source hashes are recorded. |
| Budget and credentials | Conservative all-in accounting: OpenAI $0.0964428 / $15 cap; TypeSafe $0.051170784 / $20 cap. Includes earlier checks and retained reservations, excludes subscription fees/electricity. No purchases or recharge. Configured-secret scans include raw outputs, source, paper, PDF bytes and extracted PDF text; restricted paths are excluded from Git. |
| Repository delivery | Private branch `codex/expanded-execution`, draft PR #3 stacked on PR #2/#1. Final remote state and checks are verified at handoff; this audit does not authorize merging, public publication or submission. |

Evidence paths without a directory above are under `results/expanded-execution/`.
Reproduction commands and pinned dependencies are in `paper/README.md`. Full raw
records are retained, including the overload, stream, gateway and lost-attempt cases.
Operational continuation amendments alter neither predictive settings nor saved
failures. Weak local-model outcomes remain in all applicable analyses.

The study remains a private research draft. Confidence intervals are conditional on
correlated released data, not guarantees for unseen independent tasks. LLMail fixture
support is too limited for some population intervals; those intervals are omitted.
Probability/local-model extensions are explicitly exploratory and later than original
arm outcomes. The experiment does not execute a protected assistant or measure
end-to-end attack success.
