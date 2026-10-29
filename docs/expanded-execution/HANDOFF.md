# Continue Decision Context Benchmark

Workspace: `/Users/langqi/Developer/Projects/Decision Context Benchmark`
Private repository: https://github.com/tacotuesday8888/decision-context-benchmark
Working branch: `codex/expanded-execution`, stacked on `codex/expanded-v2` (PR 2),
which is stacked on `codex/context-pilot` (PR 1). Do not merge these PRs without
shipping authorization. Commit/push/private PR management is authorized.

## Read and preserve

Read AGENTS.md, README.md, docs/expanded-v2, docs/expanded-execution/README.md,
results/expanded-execution/execution-config.json and access.json. The newer October 29
user instruction authorizes execution, superseding preparation-only restrictions.
Protect every pilot-integrity and preparation-freeze hash. The 402 eval and 60 dev
candidates, exact prompts, labels, supported contexts and settings are unchanged.
No generated examples/labels/context or tuning on evaluation outcomes.

## Credentials and cap are resolved

Both `OPENAI_API_KEY` and `TYPESAFE_API_KEY` are configured in project-only ignored
`.env.local`, mode 600. Never print, upload or commit them. Preserve other entries.
Both official providers passed two actual development requests: authentication,
model match, parsing and token usage. Do not create more keys or repeat smoke checks.
OpenAI's encrypted connector required reconnecting and then succeeded. TypeSafe's
masked old ContextBench secret could not be recovered; after explicit confirmation,
one new benchmark key was created while preserving the original. Temporary secret
setup material and clipboard state were cleaned. Legacy pilot keys are unused by
expanded execution but retained for history; no unrelated credential was revoked.

The owner's total cap is **$15 including checks and execution**, not $17+$25 credit
balances. $0.99 is reserved for checks, $14.01 for evaluation. All execution-ledger*.json
share that single evaluation cap, not one cap each. Current conservative accounting
is around $0.15; inspect live ledgers for the exact number. It deliberately overestimates
standard input rates, retains unknown reservations and assumes no discounts. No
purchases, recharge, public publication or submissions. No automatic paid chat fallback. Any deliberate route switch requires a new configuration, development validation, and remaining budget under the same $15 total cap.

## Panel: no extra providers needed

- Official TypeSafe System One `jev-1.14.0`: API key; **812/812 evaluation cells complete**.
- Official OpenAI Decisions `gpt-6-luna`: API key; **812/812 complete**.
- GPT-6 Luna Responses: authorized subscription; initial 38 cells saved, including
  one observed invalid empty response. Remaining cells are queued after Astra.
- GPT-6 Astra Responses: authorized subscription; **actively running**.
- Local `protectai/deberta-v3-base-prompt-injection-v2`, pinned immutable revision:
  **402/402 complete**, Mac CPU, no API or per-request cost. This is not Laya.

Five configurations, four distinct model IDs. Gemini and Perplexity are not needed.
Do not expand the panel merely because the user offered those alternatives.
A route change needs a new explicit configuration/version and dev validation before
its evaluation; never silently replace subscription access with paid API calls.

## Active jobs: inspect before running anything

At handoff, these processes are expected on this same Mac:

- PID 87764: `execute.py eval --config astra_chat` (initial serial process).
- PID 93165: `resume_luna_after_astra.py` waits on the original `.run.lock`, then resumes
  Luna on the same subscription and rebuilds analysis.

PIDs may finish before the next chat starts. Inspect `ps` and actual saved records.
Do not launch another process for either configuration while these are alive. Parent
chat exec sessions were 48164 and 61016, respectively; another chat can inspect OS
processes and files without those session handles. Both use this existing checkout;
do not switch branches/worktrees under live jobs. Runtime locks are Git ignored.

The Luna failure returned HTTP 200/curl exit 0 but an empty body. It is not a proven
timeout. Keep its invalid cell and original STOP.json. stop-resolution.json binds
that STOP hash and allows continuing remaining cells without retrying the invalid
cell. No evaluation-output repair or re-prompting. Native 0.5 ties are abstentions,
not binary predictions. Preserve failures and raw responses.

If a job is gone, inspect pending ledger entries, STOP markers and raw records before
resuming. Never delete a pending charge reservation to make room. A new invocation
skips completed logical cells (including invalid ones) and rejects changed routes or
payloads. Billing/auth/quota/model mismatch stops that provider; no repeated retries.
One retry only for transient transport/500/502/503/504, max 41 per remote configuration.

## Finish the requested work

1. Monitor and finish Astra and Luna. Surface real blockers; continue independent work.
2. Run offline analysis and verification. Inspect source-specific coverage and failures.
   Complete paired trusted-task effects by source and secondary neighboring-source
   effects only where authentic LLMail task2 supports them. No pooled ranking or
   balanced accuracy for one-class strata. Preserve BIPIA document/family interval
   sensitivity and LLMail team/fixture limits. Source-label caveats remain applicable.
3. Visually inspect final figures, update the concise report and handoff status. The
   current report is explicitly partial. Local detector performance is candidate-only.
4. Stage only intended sanitized artifacts, scan against configured credentials,
   commit/push and update the execution PR. Obtain green offline CI. No merge/publication
   requested. Report final complete/incomplete coverage and conservative usage cost.

Offline commands (no inference):

```sh
.venv/bin/python -m unittest discover -s tests/expanded_execution -v
.venv/bin/python -m unittest discover -s tests/expanded_v2 -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/expanded_execution/verify.py
.venv/bin/python scripts/expanded_v2/verify.py
.venv/bin/python scripts/verify_pilot.py
.venv/bin/python scripts/expanded_execution/analyze.py
```

Tests at handoff: 12 execution, 18 expanded-preparation, 29 pilot/setup tests passed;
182 protected pilot files and every preparation freeze hash matched; secret scan clean.
The new CI workflow checks execution offline and never calls an API. The report,
summary, CSV and figures are derived from saved per-attempt records. Rebuild them after
live jobs complete; do not claim final results based on the present partial snapshot.
