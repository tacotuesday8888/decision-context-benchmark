# Verification record

Completed October 26, 2026 (America/New_York).

- Primary coverage: 144 held-out request records (18 candidates × 4 conditions ×
  2 models), plus 16 development records. One GPT evaluation output is incomplete;
  all primary requests were attempted and retained.
- Operational omissions: 4 failed original Gemini development records (8 attempts)
  and 1 failed Gemini 3.7 substitution record. Neither reached evaluation. The 16
  unrun original Gemini evaluation cells are explicitly listed in summary.json.
- All 165 recorded requests match their frozen plan or separately frozen substitution
  plan. Candidate/gold/group references, raw-response parsing, caps, usage extraction
  and table/summary values passed integrity checks.
- All 29 unit/regression tests passed, including incomplete-stream handling, invalid
  predictions, score validation, paired/grouped statistics, credential refresh rotation,
  trust-boundary construction, failed-development gates and no-network resumption.
- Selected data re-extraction from the pinned upstream downloads reproduced the exact
  frozen SHA-256: e7b7cd276af357074d3044911f077d44367f402c8cf80967347297fa31e95c59.
- Fresh reproduction used a Git archive of commit `48896500195344bc9a6782db5898f5886906c1d0`, a new CPython 3.13.13
  virtual environment and requirements-pilot.lock. No credentials or environment files
  were copied. Tests, the verifier and offline analysis all passed with zero model
  requests. summary.json, per-example.csv, report.md and the substitution CSV were
  byte-identical after regeneration.
- Both PNG figures were visually inspected against the actual metrics: point estimates,
  interval types, class denominators, legend markers and explanatory notes were readable
  with no observed clipping. PDF and SVG exports are generated from the same figures.
  SVG IDs and vector metadata are deterministic; source excerpts are normalized for
  report display while raw requests/responses preserve their original content.
- Intended staged files were checked for local credential values; no matches. Credential
  files, full upstream downloads, virtual environments and historical raw smoke captures
  were excluded. The new GitHub repository was verified private with main as its default
  branch. The pilot is delivered on codex/context-pilot for review; no merge was requested.
- Added paid API spending: US$0. No payments, purchases, subscriptions or recharge changes.

CI runs only offline tests/integrity/analysis and checks that regenerated analytical
outputs match Git. Remote CI status is available on the pull request; it is not inferred
from local test success.
