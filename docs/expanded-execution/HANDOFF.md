# Continue Decision Context Benchmark

Use `/Users/langqi/Developer/Projects/Decision Context Benchmark`, the existing private
repository `https://github.com/tacotuesday8888/decision-context-benchmark`, branch
`codex/expanded-execution`, and draft PR #3. It is stacked on PR #2, which is stacked
on PR #1. Commit/push/private PR management is authorized; merging/publication is not.

## Latest owner direction

Set up and clean the project, then continue a rigorous research study of whether
**trusted context improves decision models' decisions and probability reliability**,
using prompt-injection detection as the current case study. Recognizing attacks is
not proof of end-to-end attack prevention. Do not generalize from this corpus to all
decision tasks. Explain results in plain language first, then precise technical details.

Read AGENTS.md, README.md, docs/expanded-v2, this directory's README.md and
RESEARCH-PLAN.md, and `results/expanded-execution/execution-config-v2.3.json`.
The newest instructions supersede older preparation-only and shared-cap restrictions.

## Budget and access: resolved, do not repeat setup

Independent **all-in caps: OpenAI $15; TypeSafe/Jev $20**, including earlier development,
evaluation, failures and pending reservations. These are limits, not spending targets.
The new ledger guard counts legacy and new records by provider. Old shared-cap files
remain historical evidence. No purchases, recharge, extra subscriptions, public release
or submissions. Account balances are not budgets. Ask only if a genuinely new scope
would exceed authorization; do not repeatedly ask for the already confirmed caps.

Existing project OpenAI/TypeSafe keys work and are stored only in ignored `.env.local`
with mode 600. Never print, commit or upload secrets. Reuse project subscription OAuth
for Luna/Astra; never read Codex cached credentials or silently switch routes.

## Model status and commands

- Official Jev `jev-1.14.0`: 812 eval cells saved.
- OpenAI Decisions `gpt-6-luna`: 812 eval cells saved. Luna Responses is the same
  model ID through another interface, not another independent model family.
- Astra Responses: 169 response records plus one preserved unknown interrupted attempt.
- Luna Responses: 38 saved cells, one empty-response failure. Its STOP resolution is
  bound to the original failure and permits the remaining cells, without repairing it.
- **Selected new local candidate: Nimble `nimble:9b-q4_K_M`**, official Ollama library,
  digest `d99f22c363cea449151cc473887de081b98ca98e8a29b1a8710e09da916f2c79`, runtime
  Ollama 0.40.11, native `http://127.0.0.1:11434/v1/systemone`. Local model is 5.6 GB;
  14 development cells over seven existing candidates (including longest dev input)
  succeeded with usage/probabilities and matching loaded digest. About 6.3 GB reported
  accelerator allocation; not whole-system peak RAM. No native input truncation is
  permitted by the API; oversized requests fail. No keys, cloud fallback or API charge.
  Exact config, evidence and freeze: `results/nimble-setup/`. No Nimble eval yet.
- Laya 322M: pinned SDK/checkpoint in `.venv-laya`; 120 dev cells over 60 candidates,
  all valid/untruncated, weak accuracy. Keep supplementary baseline results, not a
  best-model claim. No Laya eval. Original freeze plus integration amendment preserved.
- Protect AI: 402 completed candidate-only baseline scans; no native context factorial.

No other model downloads are needed. Abandoned Strands/Liquid exploratory downloads
were removed. Preserve unrelated global Ollama models and the older SLM workspace.
No original Astra/Luna OS process was live at setup inspection. Inspect again before
starting anything. The pending Astra ledger reservation was retained; its lost attempt
was recorded as unknown/invalid without inventing a response or retrying it. Normal
resume skips that cell. Never delete reservations or completed failures to rerun them.

Useful commands, after checking actual state:

```sh
# Start a loopback Ollama server only if none is listening; no new pull is needed.
# OLLAMA_HOST=127.0.0.1:11434 ollama serve
.venv/bin/python scripts/nimble_v2/run.py eval
.venv/bin/python scripts/expanded_execution/execute.py eval --config astra_chat
.venv/bin/python scripts/expanded_execution/execute.py eval --config luna_chat
.venv/bin/python scripts/expanded_execution/analyze.py
.venv/bin/python scripts/expanded_execution/verify.py
```

Finish these authorized prepared runs autonomously, preserving every per-attempt raw
request/response/failure. Model settings/prompts and added local arms are frozen before
held-out execution. No prompt repair, evaluation tuning, repeated billing/auth retries
or silent route fallback. If Laya evaluation is included, use its separate runner and
`.venv-laya`, and label it supplementary. Do not discard poor results.

## Data, statistics and paper work

The fixed 402 eval / 60 dev collection uses released, attributable BIPIA and LLMail
material with authentic task/context eligibility. No AI-generated examples/labels,
invented missing context or evaluation-based tuning. Published fixtures can be
synthetic; do not describe them as private real emails. Preserve every original pilot
and preparation hash. Distinguish candidates, related groups, conditions and requests.

Follow RESEARCH-PLAN.md: primary paired source-specific balanced accuracy and error
rates; paired cluster-bootstrap intervals; native probability Brier scores and reliability
plots with denominators; supplementary clipped log loss/threshold tradeoffs. Scores at
0.5 count in forecasting metrics even when classification abstains. Boolean chat outputs
are not probability forecasts. Never invent confidence scores. Probability analysis is
an exploratory amendment added after some original outcomes existed; do not call it
preregistered. No pooled winner or unsupported significance claims. Complex hierarchical
models need enough independent tasks; they are not mandatory for rigor.

Conduct a current primary-source literature review on decision models/Jev and context-aware
injection detection. Check papers against actual code/data and model versions; social
posts are leads. Inspect candidate additional published datasets before proposing a
paper-scale extension. Do not assume novelty or confuse different benchmark versions.
Any expanded paid scope must fit the remaining caps or receive new bounded authorization.
Do not expand the model panel or generate data just to make the paper larger.

Finish a concise source-stratified report, experimental trust-boundary diagram, dataset
coverage figure, paired-effect intervals, probability reliability plots, error breakdown,
and honest route-specific cost/latency. Check the visuals. Save reproducible code,
traceable sources, exact settings and limitations. Keep reports explicitly partial until
intended cells finish or genuine operational blockers are documented.

Run offline CI/tests/verifiers, scan intended artifacts against configured secrets,
commit/push and update draft PR #3. Do not merge, submit or publish publicly.
Report back with the simple meaning first, then the necessary numbers, evidence and
remaining limitations. Avoid jargon dumps and repeated proposals/permission questions.

Nimble runner robustness amendment `execution-freeze-v2.3.1.json` preserves the
original setup freeze and ensures a stopped runtime cannot erase an inference failure
when its follow-up metadata request also fails. No model/data/prompt or dev evidence changed.

Cost at setup: conservative accounted usage is $0.096443 OpenAI and $0.051171
TypeSafe, including prior checks. Remaining planned Nimble and subscription comparator
cells reserve $0 in metered API fees on the frozen routes. Local electricity and
existing subscription fees are excluded. The full-panel estimate, if started fresh,
reserves at most $1.066068 OpenAI Decisions and $0.446817 Jev including bounded
transient retries; these completed API arms must not be rerun. Any comparator switch
to paid API requires a new route configuration, estimate and development verification.
