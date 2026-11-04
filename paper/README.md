# Historical expanded-v2 draft reproduction

This directory documents the earlier expanded-v2 manuscript and PDF. These are
not the current consolidated paper. For the current results and unwritten paper
plan, see [paper preparation](../docs/paper-preparation/README.md). The commands
below reproduce only the historical expanded-v2 artifacts.

`manuscript-template.md` contains the prose and named insertion points.
`manuscript.md` and `../output/pdf/decision-context-benchmark-draft.pdf` are generated
from the saved analyses, not manually edited numerical reports. An interim build is
explicitly marked. It must not be represented as a completed experiment.

For a fresh environment, install the pinned offline dependencies (package download
requires network; regeneration itself makes no model requests):

```sh
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-expanded-v2-data.txt -r requirements-paper.txt
```

From the repository root, after inference has stopped:

```sh
.venv/bin/python scripts/expanded_execution/audit_execution.py --require-terminal
.venv/bin/python scripts/expanded_execution/analyze.py
.venv/bin/python scripts/expanded_execution/forecast_analysis.py
.venv/bin/python scripts/expanded_execution/research_summaries.py
.venv/bin/python scripts/expanded_execution/error_review.py
.venv/bin/python scripts/expanded_execution/verify_analysis.py
.venv/bin/python scripts/expanded_execution/paper_figures.py
.venv/bin/python scripts/expanded_execution/build_paper.py
.venv/bin/python scripts/expanded_execution/verify_paper.py
```

Install `requirements-paper.txt` for PDF authoring/rendering. The last command needs ReportLab (tested with 4.4.9). The other commands use the
existing project environment. No command above makes a model request. The terminal
audit intentionally fails if planned cells are missing; an operationally blocked
run requires a separately documented, explicit disposition, not a forced pass.

`build-manifest.json` binds the numerical/prose/figure inputs to generated outputs.
Review all PNG/SVG figures in `results/expanded-execution/paper-figures` and render
all PDF pages with `scripts/expanded_execution/render_paper.py` to inspect layout. The PDF was initially rendered with pypdfium2 from
the bundled document runtime. Initial renders are only layout checks, not final
verification. Final inspection must use the final artifact hashes.

Current analytical units and safeguards are in
`docs/expanded-execution/RESEARCH-PLAN.md`; inspected primary references and exact
code-source receipts are in `LITERATURE-REVIEW.md` and the corresponding results JSON.
Original pilot and preparation files remain separately frozen. No new labels,
examples, calibration fits or thresholds are introduced by the paper build.

The final isolated-export check is recorded in
`results/expanded-execution/offline-reproduction.json`: all 26 compared artifacts
were byte-identical, including PNG/SVG figures and PDF. No credential files, model
weights, or raw source downloads were copied. It used the already installed analysis
and PDF dependency runtimes, not a fresh package installation. Source hashes and
per-command outcomes are included. Final visual inspection is bound to the PDF and
figure hashes in `paper-visual-review.json`.
