# Reproduce the saved results

These commands check saved results. They do not call models or need API keys.

## Quick check

Use Python 3.13 and run from the repository root:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
.venv/bin/python -m unittest discover -s tests/critical_review -v
.venv/bin/python -m scripts.critical_review.verify --output /tmp/dcb-review.json
```

Use a new output filename if the inputs change. The verifier refuses to overwrite a different receipt.

This reproduces the compact follow-up calculations, checks saved intervals and failure handling, and reports any direct random-seed portability differences. It uses archived draws where needed; it does not silently change the historical results.

## Draw the current figures

```sh
.venv/bin/python scripts/paper_preparation.py
```

Outputs: `results/paper-preparation/` (PNG, PDF, SVG and CSV). This redraws presentation files from frozen numbers; it does not rerun experiments. File metadata can change image hashes.

## Full evidence checks

Some original page text, plans and raw provider records are intentionally local. A fresh clone cannot reproduce those checks without the retained evidence. See [data access](DATA.md) and [full review instructions](docs/critical-review/README.md).

Earlier studies have separate methods and commands:

- [761-combination study](docs/extension-v3/REPRODUCE.md)
- [Main BrowseSafe++ results](results/study-v7-execution/README.md)
- [GPT-6.1 Sol follow-up](results/subscription-followup-execution/README.md)
- [Second-source and action-pilot checks](results/subscription-followup-extensions-execution/README.md)

Do not run inference scripts, rebuild frozen plans, replace failed attempts, or treat old budget instructions as new authorization. Reproduction is different from collecting new results.
