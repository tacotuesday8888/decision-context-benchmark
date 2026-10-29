# Current execution setup

The latest October 29 instruction sets independent all-in experiment spending caps:
**OpenAI $15; TypeSafe/Jev $20**. Earlier checks and execution count toward these
limits. They are not spending targets. Historical shared-cap configuration and
ledgers remain unchanged; `execution-config-v2.3.json` is the active configuration.
The runner counts every legacy and new reservation by provider under one file lock.
There are no purchases, recharge, new subscriptions, public releases or submissions.

The primary question is whether authentic trusted task context improves decision
models' prompt-injection judgments. See [the plain-language research and statistical
plan](RESEARCH-PLAN.md) and [the continuation handoff](HANDOFF.md). The experiment does
not establish end-to-end prevention by an assistant.

## Access

- Official TypeSafe `jev-1.14.0`: existing project API key; 812 eval cells saved.
- OpenAI Decisions `gpt-6-luna`: existing project API key; 812 eval cells saved.
- Luna/Astra Responses: project-authorized subscription; no silent API-key fallback.
- **Nimble `nimble:9b-q4_K_M`**: local Ollama 0.40.11, native `/v1/systemone`, digest
  `d99f22c363cea449151cc473887de081b98ca98e8a29b1a8710e09da916f2c79`.
  Download is 5.6 GB; actual native inference succeeded in all 14 dev checks, including
  the longest development candidate. Loaded accelerator allocation was reported at
  about 6.3 GB; this is not a measured whole-system peak. No key or per-request API fee.
- Laya multilingual 322M: pinned publisher snapshot and SDK 0.4.17 in `.venv-laya`;
  120 dev cells completed without truncation. Weak zero-shot accuracy; retain as a
  supplementary baseline, not a claimed best model. No Laya eval has run.
- Protect AI: completed candidate-only specialist baseline. Do not invent a native
  context comparison or discard its poor results.

Seven registered configurations over six distinct model IDs (Luna has two interfaces).
Frozen original panel/data/prompts remain unchanged; additions are versioned execution
extensions. See local setup metadata, exact raw dev records, and freeze files.

API keys remain only in ignored `.env.local`, permissions 600. Values must never be
printed, uploaded or committed. Original pilot keys and unrelated Ollama models remain
untouched. Abandoned Strands/Liquid exploratory downloads were removed; no more models
or accounts are needed for this setup.

## Evidence and continuation

All actual provider/local attempts retain requests, responses, usage and failures.
Astra has 169 response records plus one unknown interrupted attempt. That pending
zero-metered reservation is retained. Its missing response was not fabricated and the
cell is not silently retried. Luna has 38 saved cells, including an empty-response
failure; its bound STOP resolution permits continuation of the remaining cells.
No original evaluation process is currently being relied upon as a background job.

The primary payloads, 402 eval / 60 dev collection and original pilot's 182 protected
files remain intact. Laya's original v2.2 freeze is preserved; its v2.3 integration
amendment records the shared runner/budget changes with identical model settings and
identical saved dev responses. Nimble has its own dev-first freeze; no Nimble held-out
model inference has run during setup.

Run only explicit configurations after inspecting saved state:

```sh
# Native local metadata/server; start a loopback server only if none is listening.
ollama --version
# OLLAMA_HOST=127.0.0.1:11434 ollama serve
.venv/bin/python scripts/nimble_v2/run.py eval
.venv/bin/python scripts/expanded_execution/execute.py eval --config astra_chat
.venv/bin/python scripts/expanded_execution/execute.py eval --config luna_chat
```

Completed cells, including invalid ones, are skipped. Failed auth/billing/quota/model
identity stops a provider; no repeated retries or purchases. Only bounded transient
transport/500/502/503/504 retry rules from the frozen protocol apply. Local Nimble
uses only loopback, disallows redirects/proxies, checks the exact digest/runtime, and
has no chat/cloud fallback. Native local API rejects inputs that exceed its context
rather than silently truncating. Runtime failure is preserved, not repaired by a
follow-up prompt. No full evaluation is launched automatically by setup.

Offline checks (no model loading, downloads, keys or inference):

```sh
.venv/bin/python -m unittest discover -s tests/expanded_execution -v
.venv/bin/python -m unittest discover -s tests/nimble_v2 -v
.venv/bin/python -m unittest discover -s tests/laya_v2 -v
.venv/bin/python -m unittest discover -s tests/expanded_v2 -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/expanded_execution/verify.py
.venv/bin/python scripts/expanded_v2/verify.py
.venv/bin/python scripts/verify_pilot.py
```

Rebuild derived partial reports offline with `scripts/expanded_execution/analyze.py`.
A report must stay explicitly partial until intended cells are completed or operational
blockers are documented. Probability scoring helpers are tested; implement the paired
probability analysis under the exploratory amendment before writing final conclusions.

Nimble runner robustness amendment `execution-freeze-v2.3.1.json` preserves the
original setup freeze and ensures a stopped runtime cannot erase an inference failure
when its follow-up metadata request also fails. No model/data/prompt or dev evidence changed.
