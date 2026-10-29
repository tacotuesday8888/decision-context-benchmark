# Extension v3: active work, not completed confirmation

Branch `codex/context-extension-v3`, based on completed-study commit
`ab3fff2623177327d5fe58eb19a974af7d5dc7e8`. The goal objective is the owner's
`d0567430-d8c8-4dfb-ab3f-e853b591f9ec/goal-objective.md` attachment. Read that
objective before continuing. It authorizes broader empirical work under existing
independent all-in OpenAI $15 / TypeSafe $20 caps. No purchases or new subscriptions.
No paid calls have been made by v3. Prior all-in accounted spending remains
$0.0964428 OpenAI and $0.051170784 TypeSafe, including preserved historical records.

All 5,793 previously tracked files are hash-protected in
`results/extension-v3/completed-study-freeze.json`; integrity verification passed.
Do not modify old outputs, protocols, source code, paper or PDF. The completed
study had 5,274 terminal cells; it is not an unfinished run to resume.

## Completed new work

- Reproducible AgentDyn trace audit and provenance inventory, pinned source revision.
  648 trace files in one published pipeline, 28 attacker-goal baselines excluded.
  1,152 tool-message occurrences, 739 distinct byte strings, 1,077 distinct
  task/text pairs, 60 distinct task IDs. **None approved for evaluation yet.**
  454 unique attacked texts and 285 no-attack texts. Shared normalized candidates
  link 59 tasks; one task is isolated. One task ID has different user wording
  between its baseline and attacked trace. Preserve trace-specific wording.
- Six offline source-parser regression tests passed. No upstream code executed.
- Frozen development-only local diagnostic: 42 new requests on seven previously
  used development candidates, all completed. Original baseline responses reused.
  Nimble statement variant errors 8→6 /14; Laya statement and explicit-criteria
  variants both 7→8 /14. Brier changes: Nimble −0.0330222, Laya statement +0.0393370,
  Laya criteria −0.000195125. These pooled diagnostic counts are descriptive,
  not population estimates; source/condition results and every score are saved.
  No supported claim of a corrected implementation or general improvement.
- Laya SDK inspection: noul is P(true), false/true option order, output p[1].
  Its model card accepts question syntax. No probability-direction bug found.
  Both existing adapters enforce identity and input coverage. Diagnostics retain
  backend, quantization, tokenizer, thresholds and calibration unchanged.

## Source investigation

Local clones are ignored under `data/raw/extension-v3/`; do not commit whole clones.

| Source | Pinned revision | Evidence / disposition |
|---|---|---|
| InjecAgent | `f19c9f2c79a41046eb13c03c51a24c567a8ffa07` | MIT in LICENCE; 1,054 base cases are 17 user fixtures crossed with 62 attacker instructions. Enhanced variants repeat these. No clean filled user response released in inspected user fixtures; do not invent benign fills. |
| AgentDojo | `357c80dea9af34323f709c3505d9e6d224654c7e` | MIT; inspect version overrides before counting tasks. Official result explorer linked, raw runs not found in inspected clone. |
| AgentDyn | `5353cf7615b135cace8d07c8f12dac53a16b6db3` | MIT root license read; source has 60 new task fixtures and 560 task/attack cases across GitHub, shopping, daily life. Released runs repeat models/defenses. Audit uses only gpt-4o-mini-2024-07-18. |

AgentDyn `important_instructions_attacks.py` constructs one common impersonation
template. The default injection-vector YAML contains ordinary messages/reviews/ads.
Some tool outputs are action acknowledgments, not useful difficult benign documents.
Inspect semantic eligibility and first injected encounter before selecting examples.
Never use attack-success `security` or utility as detector gold. Source inspection
also found an apparently copied `send_money` ground-truth stub for a GitHub starring
attack; this does not invalidate the saved text but matters for prevention replay.
Do not launch the environments until execution semantics are independently audited.

## Next required work

1. Finish source-specific eligibility, license exceptions, duplicate/related-group
   checks. AgentDyn likely belongs wholly in fresh confirmation, not a random
   task split; consider first encountered injection and content-bearing clean tools.
   Preserve original text and actual user task, exclude downstream attack effects.
2. Inspect remaining authentic new sources / AgentDojo traces, and implement
   InjecAgent extraction without fabricating clean context. Distinct task coverage
   matters more than reaching thousands by cross products.
3. Finish current literature comparison and audit backend/default calibration.
   Do not select prompt variants solely from the seven-candidate operational check.
4. Define development policy, paired controls, clustering-aware precision, exact
   requests/token estimates and provider accounting including all earlier ledgers.
   Freeze confirmation before any held-out calls. No v3 confirmation authorized by
   a frozen protocol yet; the owner has authorized designing and running one.
5. Execute justified extension, source-specific analysis and inspected figures;
   retain failures. No new manuscript/PDF before core work finishes.
6. Commit/push and maintain a new private draft PR stacked on expanded-execution;
   do not merge/publicly publish. Goal remains active.

Reproduce current checks:

```sh
python3 scripts/extension_v3/source_audit.py
python3 -m unittest discover -s tests/extension_v3 -v
python3 scripts/extension_v3/analyze_diagnostic.py
python3 scripts/extension_v3/integrity.py
```

Both local diagnostic processes have exited successfully. Do not repeat requests.
Their runners skip completed records and reject failed/interrupted reservations.

## Latest checkpoint

Private draft PR #4 is open, stacked on `codex/expanded-execution`:
https://github.com/tacotuesday8888/decision-context-benchmark/pull/4
Commit `6b21aca` pushed; all six inherited CI checks passed. The new six tests ran
locally (existing workflows do not yet discover the separate v3 test directory).

After that checkpoint, added reproducible InjecAgent inventory: 1,054 distinct
published base texts, 17 tasks/templates, 62 attack instructions; still no final
eligibility/gold assignments. Its original prompted-agent evaluator interpolates
`Tool Response` verbatim; retain serialization quotes, do not prettify it.

Important new related-work/source lead: `benign-instruction-bench`, pinned revision
`5d0ae7c438a7b01be2ac0a2e8bc943e45c8f851f`, under ignored raw directory. Read the new
research-notes section before proceeding. It already includes task-aware and
no-request judge variants, replayed AgentDojo/tau-bench, and updated clustered
analyses. Its clean AgentDojo replay may provide 97 additional authentic task
fixtures without LLM generation. No upstream code has run. Review network/tool
side effects before a bounded offline replay; pin dependencies in a new ignored
environment under `data/raw/extension-v3/` so old environments remain unchanged.

Reject `buried-injections` as a source of authentic task/document pairs: actual
loader rotates default documents arbitrarily across tasks. Preserve its relevance
to related work, not its advertised counts as eligible data.

AgentDyn content-tool/first-matched-attack exploratory filter yielded 542
occurrences /359 distinct texts (422 first attacked responses and120 clean
content-bearing responses). This is not frozen selection. Some read_file outputs
are published synthetic account fixtures; avoid printing their contents again.
No secrets from this workspace were read. A proper final adapter still needs
first-encounter checks, licensed extraction, exclusions and label review.

## Offline AgentDojo replay completed after the source review

`scripts/extension_v3/replay_agentdojo.py` now runs the pinned official clone's
ground-truth user calls, in memory, with socket connections/DNS disabled and
credential-like environment variables removed before importing SDKs. No LLM or
real service used. Environment created only inside the ignored clone with
`uv sync --frozen --no-dev --project data/raw/extension-v3/agentdojo --python 3.12`.
It uses the upstream frozen lock; package versions and lock hash are in the receipt.

Observed 337 outputs /150 distinct texts from96 of97 tasks. Suite occurrences:
workspace82, travel124, banking33, slack98. Original data and arguments remain in
ignored `data/raw/extension-v3/agentdojo-clean-replay.jsonl`; tracked inventory
contains only provenance/hashes. No gold labels assigned yet. Content eligibility,
grouping, and frozen selection remain required. Current upstream default formatter
is JSON, unlike the older paper's YAML representation: record this difference.

Preserved failure: workspace:user_task_10 ground_truth raises AttributeError.
Cause established in source: calendar.current_day is declared str, but task calls
`.isoformat()` on it. Do not silently fix the upstream fixture or invent outputs.
No downstream calls for that task were attempted. This is a one-task exclusion,
not a blocker for all other source preparation.

Current branch includes a dedicated new v3 CI workflow. At commit0bc267c, all eight
push/PR checks passed, including both v3 integrity/test/reproduction jobs. No
inference process is live. The v3 goal remains active and confirmation remains
unfinished; continue extraction/validation and design, not another paper build.
