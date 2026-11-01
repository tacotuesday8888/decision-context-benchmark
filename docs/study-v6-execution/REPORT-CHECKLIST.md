# Reporting operations after terminal execution

This is an operational guide, not a protocol amendment or empirical report. It is
outside the frozen scientific document list. Do not edit frozen code, requests,
reviews, analysis choices or historical receipts to make reporting pass. Only the
root executor may dispatch inference; the commands below concern completed evidence.

## Terminal evidence first

Run from the Decision Context Benchmark repository using its existing `.venv`:

```sh
.venv/bin/python scripts/study_v6/freeze.py verify-confirmation
.venv/bin/python scripts/study_v6/verify_execution.py
```

The execution verifier independently reparses retained raw responses and replays
the reservation journal. An intact but incomplete run returns `ready=false`.
Corruption raises instead of becoming a missing observation. Do not write final
analysis inputs until `ready`, `integrity_checks_passed` and `journal_terminal`
are true, with no unexplained unattempted cells.

Readiness requires every scheduled eligible comparator request key for each of
Luna chat, Astra chat, Laya, Nimble and ProtectAI to have a terminal disposition.
This is the frozen comparator cohort, not just the attained paid main prefix.
Case-level refusals, invalid formats and output limits are retained outcomes.
Systemic stops require preserved stop evidence and either an approved bounded
continuation or a legitimate terminal-unrun disposition. An unfinished comparator
is not automatically complete because a paid allocation reached its cost stop.

For a genuinely terminal systemic stop, the existing accounting-only
`run.py close-stopped` path can settle dispatched evidence and cancel positively
unsent holds without a network call. The separate ignored `terminal-unrun.json`
must use the existing study version, a nonempty reason, the exact immutable active
or archived `STOP.json` SHA-256, and explicit allocation/configuration scopes. Its
stop cannot also have an activated continuation. Do not remove a stop, invent
completion, or classify a reservation as free merely because a response is absent.
The actual scope and reason require the executor's evidence-based disposition.

After every gate passes:

```sh
.venv/bin/python scripts/study_v6/verify_execution.py --write
```

This writes immutable normalized primary records and per-cell disposition detail
under ignored `data/raw/study-v6/execution-v1/`, plus the safe aggregate
`results/study-v6-execution/execution-verification-v1.json`. All first attempts
remain primary; no wrong answer is rerun or replaced.

## Construct the analysis input without shrinking its denominator

Use **all** `cells` from `confirmation-frozen-plan.json` as the planned input.
Keep unsupported and unrun cells. The verifier's `normalized-records.jsonl`
contains eligible confirmation cells, including terminal `not_attempted` or
cancelled dispositions; it excludes frozen ineligible cells. The analysis join
supplies missing/unsupported dispositions for the latter. Development never enters
confirmation analysis. Do not filter planned rows to attempted or valid rows.

Generate literal baselines using the preserved v3 resolved corpus, not the derived
execution grouping file. Their CLI deliberately checks the v3 resolution hash;
their actual source IDs are selected by the frozen intended plan. This preserves
the original source rows while excluding execution-held components from selection.
The baseline rules remain candidate-only, Boolean, uncalibrated and zero-cost.

The following sequence is for the executor after terminal verification. It creates
only ignored postprocessing files and invokes no model:

```sh
.venv/bin/python - <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.study_v6.evidence import immutable
from scripts.study_v6.freeze import verify

root = Path.cwd()
raw = root / 'data/raw/study-v6/execution-v1'
receipt, frozen = verify('confirmation')
terminal = json.loads((root / 'results/study-v6-execution/execution-verification-v1.json').read_text())
assert terminal['ready'] and terminal['integrity_checks_passed'] and terminal['journal_terminal']
intended = raw / 'intended-plan.json'
plan_sha = hashlib.sha256(intended.read_bytes()).hexdigest()
subprocess.run([
    sys.executable, str(root / 'scripts/study_v6/baselines.py'),
    '--resolved', str(root / 'data/raw/study-v6/review-resolution-v3/resolved.jsonl'),
    '--resolution', str(root / 'results/study-v6-review-resolution/resolution-final.json'),
    '--intended-plan', str(intended), '--plan-sha256', plan_sha,
    '--output-dir', str(raw / 'baselines-v1'), '--write',
], check=True)

def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def body(values):
    return b''.join(json.dumps(value, sort_keys=True, ensure_ascii=False,
                              separators=(',', ':'), allow_nan=False).encode() + b'\n'
                    for value in values)

planned = frozen['cells'] + rows(raw / 'baselines-v1/cells.jsonl')
records = rows(raw / 'normalized-records.jsonl') + rows(raw / 'baselines-v1/records.jsonl')
assert all(row['split'] == 'confirmation' for row in planned)
for values in (planned, records):
    keys = [(row['id'], row['config'], row['condition']) for row in values]
    assert len(keys) == len(set(keys))
immutable(raw / 'analysis-v1/planned.jsonl', body(planned))
immutable(raw / 'analysis-v1/records.jsonl', body(records))
PY

.venv/bin/python scripts/study_v6/analyze.py \
  --planned data/raw/study-v6/execution-v1/analysis-v1/planned.jsonl \
  --records data/raw/study-v6/execution-v1/analysis-v1/records.jsonl \
  --output data/raw/study-v6/execution-v1/analysis-v1/analysis.json
```

Do not interpret analysis `observed_cells` as model calls: it counts supplied
normalized records, including explicit terminal-unrun cells and literal rules.
Model calls, unique attempts, logical references, valid outputs and source rows
have different denominators. Use the terminal execution receipt and journal for
actual attempts/costs. Exact-payload deduplication must not multiply costs, while
all source/condition references remain in analysis denominators.

Baseline-versus-native candidate comparisons use the existing same-condition,
same-row, supported intersection with intact source pairs. The baseline's full
main target is not interchangeable with the native candidate diagnostic subset.
Keep distinct source strata and do not pool headline accuracy across constructs.

## Independently verify the scientific calculations

`verify_execution.py` verifies transport evidence, accounting and token contrasts;
it does **not** independently verify statistical results. Re-running `analyze.py`
alone also does not establish independent recomputation. Have a separate
read-only implementation check the normalized records against the retained raw
first attempts, frozen plan and terminal receipt before setting
`analysis_recomputed=true`.

Independently check these bindings and calculations:

- Preserve exact source, configuration, condition, final component, source-pair,
  admitted semantic label and upstream label. Source labels are normalized numeric
  compatibility values; original strings remain in source artifacts. Their
  agreement is conditional on agreement-based admission, not independent label
  validation or human gold.
- For each primary contrast, compute control-minus-task row errors on common
  valid condition pairs. Average within final component and class, average
  component means separately within each class, then weight classes equally.
  Preserve the declared row-level primary endpoint, source-pair attrition and
  separately reported complete-sourcepair-only sensitivity.
- Recompute full planned-denominator bounds: an unknown error lies in `[0,1]`;
  retain known errors and apply the same planned component/class denominators.
  Missing a whole gold class means no balanced estimate or balanced bound;
  retain available FPR/FNR, raw support and missing dispositions.
- Flip one shared sign for both classes within a final component. The component
  contribution uses its class mean divided by the number of represented
  components in that class, with equal class weighting. Do not treat duplicated
  rows or a large family as extra independent units.
- Match the frozen random-number recipe for exact reproducibility: NumPy seed
  `20261031`, exact enumeration through twenty nonzero component contributions;
  otherwise one hundred thousand `int8` sign draws in batches of five hundred
  twelve with the +1 correction. Bootstrap uses seed `20261032`, twenty thousand
  whole-component index draws in batches of two hundred fifty-six, recomputing
  class denominators and reporting omitted missing-class draws. Check both
  pointwise and six-test Bonferroni percentile intervals.
- Retain the fixed six primary Holm slots, with unavailable tests occupying their
  conservative multiplicity positions. Small-group results and route comparisons
  remain descriptive. Native ties abstain; chat outputs have no invented score.
  Independently check AUROC half-credit ties, Brier and fixed reliability bins.
- Reconcile FPR/FNR, valid/planned support, paired transitions, both-correct source
  pairs, complete-sourcepair sensitivity, every reviewer subgroup support gate,
  common route intersections and every proposed numerical paper claim.

The checked analysis receipt must use the **canonical JSON object digest** expected
by `figures.digest`/`paper.digest`, not the SHA-256 of pretty-printed file bytes.
Record file hashes separately for provenance. Only after actual verification set
`analysis_recomputed`, `terminal_execution_verified`, `accounting_verified`,
`label_provenance_verified` and `freeze_verified` to true.

## Export safe aggregate tables and figures

Keep the complete analysis/per-group detail ignored. The frozen figure adapter
strictly allowlists safe aggregate fields. It rejects empirical output without the
checked analysis digest and the five verification flags above.

The locked `resolution-final.json` describes **v3 review admission**. Supplemental
execution grouping exclusions are recorded separately in
`grouping-admission-v1.json`. Preserve both stages. Do not silently substitute the
v3 review target or denominators for final execution admission or attained model
coverage.

After independent checks, use `figures.build_tables(analysis,
resolution=locked_v3_resolution, verification=analysis_verification)` in memory.
Keep its base `source_attrition` as the locked v3 stage, and attach separately
checked aggregate subtrees before calling `figures.export(final_tables, directory)`:

- `execution_admission`: safe source-specific prepared, v3-review-admitted,
  additional-grouping-excluded and final-execution-admitted rows, final split/group
  support and classes, from the grouping admission receipt. Keep the stages named.
- `execution`: target, runnable, admitted common prefix, unrun groups and precise
  terminal scope/coverage counts from the execution-verification receipt. Retain
  all intended target denominators in missingness claims.
- `exact_dispositions`: aggregate ignored
  `raw-execution-verification.json.planned_cell_dispositions` by split, source,
  configuration and condition, retaining **precise status and reason codes**.
  Never include IDs, source text, exception bodies or mappings. Frozen figures
  collapse some codes into `other_parser_failure`; keep actual unsupported limits,
  invalid formats, provider incompletes, interrupted streams, refusals, ties,
  truncation and not-attempted reasons distinct in this checked companion table.
  Do not merge planned exclusion, unsupported capacity, model/output failure and
  unrun budget/systemic scope. Preserve input/output truncation scope separately
  where retained raw parser evidence supports it.
- `accounting`: provider-specific incremental conservative accounting, returned
  usage estimates, retained unknown holds, cancelled unsent requests, inherited
  totals and caps from the terminal receipt. Invoice charges stay unknown if not
  independently available. Keep exact decimal source strings; any numeric display
  fields used in paper claims must be explicitly checked conversions.
- `route_metadata` / `source_revisions`: allowlisted, verified route/model/revision
  identifiers needed for exact paper descriptions. Requested/returned identifiers,
  actual access route and evidence of access remain separate from physical weight
  identity, source training exposure and scientific results.

Check aggregate extensions independently and pin their source receipt hashes. The
final tables must retain `version`, `analysis_set`, `empirical_checks_complete`,
`review_resolution_complete` and `analysis_sha256`. Calculate the final canonical
`tables_sha256` only after extensions are complete. Do not then reconstruct through
the `figures.py` CLI, which would discard the added subtrees; call its frozen
`export` API on the final checked object. It writes the exact tables and standalone
figures. A changed artifact requires a new version/output directory; do not
overwrite conflicting results.

Immediately before the **first empirical PDF authoring command**, run the PDF
skill marker successfully exactly once. `figures.export` creates up to four PDFs
before the paper, so mark before that first empirical figure export, counting the
anticipated figure PDFs plus the final paper: normally five. Adjust the count to
the actual expected PDF outputs if a figure is unavailable. Do not mark read-only
validation, and do not repeat the marker when authoring the paper later.

```sh
DCB_V6_PDF_NODE="/Users/langqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
DCB_V6_PDF_MARKER="/Users/langqi/.cache/codex-runtimes/codex-primary-runtime/plugins/openai-primary-runtime/plugins/pdf/skills/pdf/container_tools/mark_artifact_operation_started.mjs"

# Immediately before the first empirical figures.export authoring command; run once.
"$DCB_V6_PDF_NODE" "$DCB_V6_PDF_MARKER" \
  --operation-kind create --expected-output-count 5 --output-format pdf
```

Inspect actual rendered plots for intervals, units, labels, signs and complete/
planned denominators. The source-attrition figure renders the base v3 review stage;
its paper caption must identify that stage and point to the separate execution
attrition table. No chart may imply that conditional server coverage is a native
tokenizer certificate or that a normal precision scenario is achieved power.

## Final authored paper and PDF

Only after terminal evidence, accounting, independent analysis and figure review
may the root author the final narrative. Follow `paper.py` and the pure schema
example in `tests/study_v6/test_paper.py`; do not render the synthetic fixture.

Use the five ordered roles: question/context, data/methods, primary results,
source diagnostics, discussion/references. Every page needs authored paragraphs.
Use claim-ledger tokens for numerical prose/tables, checked source-population paths
and exact expected values. A `pp` format consumes values already in percentage
points; `percent` consumes fractions. Model IDs with digits require checked
`literal` claims under `route_metadata`/`source_revisions`. Citations use readable
structured IDs and checked primary references. Keep rewritten/synthetic provenance,
agent/source agreement, selection bias, uncertainty and construct limits explicit.

The paper verification receipt adds the canonical narrative/table digests and
`narrative_verified=true` to the checked analysis gates. Every embedded figure must
have an approved PNG path, file SHA-256, matching final `tables_sha256`, and
`visually_verified=true`. Validate without authoring first:

```sh
.venv/bin/python scripts/study_v6/paper.py \
  --narrative data/raw/study-v6/execution-v1/report-v1/narrative.json \
  --analysis data/raw/study-v6/execution-v1/analysis-v1/analysis.json \
  --tables results/study-v6-execution/report-v1/tables.json \
  --verification data/raw/study-v6/execution-v1/report-v1/paper-verification.json
```

The PDF skill marker has already run before the first empirical figure export;
**do not repeat it for paper authoring**. The bundled PDF Python has
ReportLab/pypdf; the repository `.venv` need not acquire authoring dependencies.
The current host path and final-paper command are:

```sh
DCB_V6_PDF_PY="/Users/langqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

"$DCB_V6_PDF_PY" scripts/study_v6/paper.py \
  --narrative data/raw/study-v6/execution-v1/report-v1/narrative.json \
  --analysis data/raw/study-v6/execution-v1/analysis-v1/analysis.json \
  --tables results/study-v6-execution/report-v1/tables.json \
  --verification data/raw/study-v6/execution-v1/report-v1/paper-verification.json \
  --output output/pdf/decision-context-benchmark-v6.pdf --write
```

The CLI also verifies the committed confirmation freeze. If dependency discovery
returns a different runtime location later, use its returned paths.

The builder checks five-page count and extracted headings/tokens. It retains an
overflow temporary PDF for diagnosis and refuses to overwrite an existing final
paper. These checks do not replace Poppler rendering and visual inspection of
every actual page. Use the bundled `pdfinfo` and `pdftoppm` override binaries:

```sh
DCB_V6_PDF_BIN="/Users/langqi/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override"
"$DCB_V6_PDF_BIN/pdfinfo" output/pdf/decision-context-benchmark-v6.pdf
"$DCB_V6_PDF_BIN/pdftoppm" -png -r 140 \
  output/pdf/decision-context-benchmark-v6.pdf tmp/pdfs/decision-context-benchmark-v6
```

Inspect margins, tables, intervals, references, page numbering and glyphs, then
verify every numerical claim against the checked ledger. Capture the API's full
validation/output hash receipt if needed; the CLI prints only a compact result.

No public publication, submission, historical-stack merge or new paid inference
is authorized by this reporting guide. Private delivery follows the existing
dependent PR workflow, with raw material and per-row evidence remaining ignored.
