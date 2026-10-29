# Research draft reproduction

`manuscript-template.md` contains the prose and named insertion points.
`manuscript.md` and `../output/pdf/decision-context-benchmark-draft.pdf` are generated
from the saved analyses, not manually edited numerical reports. An interim build is
explicitly marked. It must not be represented as a completed experiment.

From the repository root, after inference has stopped:

```sh
.venv/bin/python scripts/expanded_execution/audit_execution.py --require-terminal
.venv/bin/python scripts/expanded_execution/analyze.py
.venv/bin/python scripts/expanded_execution/forecast_analysis.py
.venv/bin/python scripts/expanded_execution/research_summaries.py
.venv/bin/python scripts/expanded_execution/error_review.py
.venv/bin/python scripts/expanded_execution/verify_analysis.py
.venv/bin/python scripts/expanded_execution/paper_figures.py
python scripts/expanded_execution/build_paper.py
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
