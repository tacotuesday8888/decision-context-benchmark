# Reproduce expanded v2 preparation

This directory documents completed preparation, not expanded evaluation results.
The original pilot is preserved and checked against 182 recorded file hashes.
Five configurations use four distinct model IDs; the API shopping list distinguishes
required metered APIs, reusable subscription access and a free local specialist.

## Credential-free offline checks

Python 3.13. No model/API calls or weight downloads occur in these commands:

```sh
uv venv .venv-data --python 3.13
uv pip install --python .venv-data/bin/python -r requirements-expanded-v2-data.txt
.venv-data/bin/python -m unittest discover -s tests/expanded_v2 -v
.venv-data/bin/python scripts/expanded_v2/verify.py
```

`.venv-data/` is local and must remain ignored. Tests use the selected, attributed
published data and saved development responses. They verify provenance, split/group
exclusion, published insertion reconstruction, supported trust boundaries, payload hashes,
strict parsing, score ties, stream truncation, window coverage and paid-execution blocking.
The original pilot tests remain separate and pass independently.

## Rebuild from upstream sources

```sh
.venv-data/bin/python scripts/expanded_v2/prepare.py
.venv-data/bin/python scripts/expanded_v2/panel.py
.venv-data/bin/python scripts/expanded_v2/plan.py
.venv-data/bin/python scripts/expanded_v2/shopping.py
.venv-data/bin/python scripts/expanded_v2/verify.py
```

Preparation downloads roughly 580 MB of pinned public LLMail sources plus small BIPIA
files to ignored `data/raw/expanded-v2/`, reusing immutable local downloads where present.
It never executes source examples or asks a model for labels. Existing collection/source
manifests cannot be silently replaced with changed data. Source/selection hashes, raw
membership, attribution and license are in `data/expanded-v2/`. Each dataset component
retains its own notice; the mixed selection is not wholly MIT.

## Local detector / development tooling

The tested arm64 host has 16 GiB RAM. Full local runtime dependencies (including
PyTorch, Transformers and tokenizers) are recorded in `requirements-expanded-v2.lock`.
Use the publisher's exact revision in the model panel; no remote code is trusted.
Install the full tested runtime and download only the selected safetensors/tokenizer
files with:

```sh
uv pip install --python .venv-data/bin/python -r requirements-expanded-v2.lock
.venv-data/bin/python scripts/expanded_v2/download_local.py
```

A future machine must download those weights legitimately before using the adapter;
current verification intentionally does not require them. Native local inference needs
no API key, paid service, subscription, or GPU rental. On Linux, choose the CPU PyTorch
build if local inference is desired; the tested runtime lock reflects this macOS host.

Saved bounded development records already establish 8 successful Luna subscription
calls, 4 Astra subscription calls, 6 local standard scans and 2 local long-window scans.
Those are development checks, not evaluation metrics. Do not rerun live development
merely to reproduce the report. The subscription utility is capped at 12 total calls,
uses only project-authorized OAuth, and never falls back to a paid API key.

`adapters.py` implements first-party Jev, Decisions, Responses payloads/parsers and the
native local detector. `paid_execute` deliberately refuses inference in this preparation.
First-party Jev and Decisions cannot be inference-verified before funded keys are ready.
A subsequent authorized run must validate those providers on development data first,
respect a concrete spending cap, and use a new run/version if prompts, budgets or routes
change. Do not delete or overwrite saved evidence to make a new run look like a replay.

## Outputs and scope

- `data/expanded-v2/collection.jsonl`: 462 total selected candidates, with per-row
  context support, provenance labels, source groups and licensing.
- `manifest.json`, `sources.json`: deterministic membership and pinned source checksums.
- `model-panel.json`, `prompts.json`: exact configurations and shared question/schema.
- `results/expanded-v2/request-plan.json`: 3,248 planned evaluation remote requests,
  plus 402 local candidate scans (445 exact tokenizer windows). Full development plans
  are separate. Candidate counts are not request counts or independent group counts.
- `budget.json`: source-backed rate assumptions, per-phase estimates, and bounded retries.
- `development/`, `local-development.json`, `local-window-development.json`: actual
  development checks. `access.json` distinguishes catalog, authentication and inference.
- `preparation-freeze.json`: immutable prepared design/code/data hashes, explicitly not
  clearance for paid execution or a claim of completed expanded evaluation.
- `verification.json`: offline integrity and pilot preservation checks.

Some strata have only one gold class or very few benign records. Source/both comparisons
exist only in the fixed LLMail replication stratum; most sources support candidate/task,
and benign stress/local-specialist input supports candidate only. These omissions are
intentional, not filled with invented task context or copied scores.
