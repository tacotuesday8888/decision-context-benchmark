"""Render final source-specific tables only after full execution and analysis checks."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'
CONFIGS = ['jev_firstparty', 'luna_decisions', 'laya_local', 'nimble_local',
           'luna_chat', 'astra_chat', 'protectai_local']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effect_cell(effect):
    if effect is None:
        return 'Not applicable'
    point = effect['task_weighted']
    if point is None:
        return 'No complete pairs'
    scale, digits = (100, 2) if effect['metric'] == 'error' else (1, 4)
    value = f"{point['estimate'] * scale:+.{digits}f}"
    interval = point['interval']
    value += (f" [{interval[0] * scale:+.{digits}f}, {interval[1] * scale:+.{digits}f}]"
              if interval is not None else ' [too few groups]')
    return value + f"; {effect['complete_pairs']}/{effect['planned_pairs']} pairs"


def main():
    closure_path = OUT / 'execution-closure-v1.json'
    if not closure_path.exists():
        raise RuntimeError('Final report requires full terminal execution closure')
    closure = json.loads(closure_path.read_text())
    assert closure['status'] == 'terminal' and closure['terminal_required']
    assert not any(closure[k] for k in ('unattempted_or_missing', 'pending_reservations', 'in_flight_records'))
    assert closure['ledger_sha256'] == sha(OUT / 'inference-ledger-v1.json')
    inputs = {str(closure_path.relative_to(ROOT)): sha(closure_path)}
    reports = {}
    for config in CONFIGS:
        path = OUT / 'analysis' / (config + '.json')
        report = json.loads(path.read_text())
        for suffix in ('verification', 'record-audit', 'bootstrap-verification'):
            if suffix == 'bootstrap-verification' and config == 'protectai_local':
                continue
            receipt_path = path.with_name(config + '-' + suffix + '.json')
            receipt = json.loads(receipt_path.read_text())
            assert receipt['status'] == 'passed'
            if suffix == 'record-audit':
                assert receipt['record_sha256'] == report['record_hashes']
            else:
                assert receipt['analysis_sha256'] == sha(path)
            inputs[str(receipt_path.relative_to(ROOT))] = sha(receipt_path)
        for name, digest in report['record_hashes'].items():
            assert sha(ROOT / name) == digest
        inputs[str(path.relative_to(ROOT))] = sha(path)
        reports[config] = report
    manifest_path = OUT / 'collection-manifest-v1.jsonl'
    manifest = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    inputs[str(manifest_path.relative_to(ROOT))] = sha(manifest_path)
    groups = defaultdict(list)
    for row in manifest:
        groups[row['dataset']].append(row)
    lines = ['# Decision Context Benchmark — extension v3 results', '',
        'The frozen confirmation is fully attempted. Task context has source- and model-specific effects; '
        'neither a universal benefit nor a universal model winner follows. Crucially, some '
        'task-versus-candidate gains disappear against an empty task field or a generic reminder. '
        'Thus the candidate baseline alone does not establish a benefit from meaningful task information. '
        'The tables below report the predeclared paired effects, including negative and inconclusive findings.', '',
        'What we learned: Astra misses fewer InjecAgent attacks when given the task, but the small '
        'direct-harm control subset shows no advantage over reminders or scrambled tasks. Jev has a '
        'similar distinction between candidate-baseline gains and control comparisons. Some Luna Decisions '
        'and Nimble probability comparisons remain favorable, with broad uncertainty. Laya often worsens '
        'on clean-source probability loss. These are useful differences between sources and interfaces, '
        'not a single leaderboard result. Better relative performance can still leave many attacks missed: '
        'Luna chat misses 103 of 128 valid direct-harm task examples.', '',
        f"The collection contains {len(manifest)} task/text pairs, "
        f"{len({r['candidate_sha256'] for r in manifest})} distinct texts and "
        f"{len({r['groups']['task'] for r in manifest})} task groups. "
        f"Confirmation contains {sum(r['logical_requests'] for r in reports.values()):,} attempts across "
        'seven configurations/six model IDs; Luna has two interfaces. '
        'The separate 108 control-development requests and 42 local diagnostic calls are not evaluation examples.', '',
        'Labels inherit published clean/default versus intended-injection construction. They are not '
        'independent semantic adjudications, real private production messages, or measured attack success. '
        'We generated no benchmark examples or gold labels and invented no missing context. Published source constructions remain explicit.', '',
        '## Source coverage', '', '| Source | Task/text pairs | Distinct texts | Tasks | Clean / injected |',
        '|---|---:|---:|---:|---:|']
    for source, rows in sorted(groups.items()):
        labels = Counter(r['gold'] for r in rows)
        lines.append(f"| {source} | {len(rows)} | {len({r['candidate_sha256'] for r in rows})} | "
                     f"{len({r['groups']['task'] for r in rows})} | {labels[0]} / {labels[1]} |")
    lines += ['', 'Task groups and texts recur across strata; do not sum columns as independent sample sizes. '
        'AgentDojo is clean-only and InjecAgent attack-only. False-positive or false-negative rates '
        'are undefined when their denominator class is absent.', '', '## Completed attempts', '',
        '| Configuration | Planned attempts | Parsed status counts | Reported input / output tokens | Requests with usage |', '|---|---:|---|---:|---:|']
    for config, report in reports.items():
        statuses = Counter()
        input_tokens = output_tokens = usage_records = 0
        for name in report['record_hashes']:
            record = json.loads((ROOT / name).read_text())
            statuses[record.get('parsed', {}).get('status', 'runtime_error')] += 1
            usage = record.get('parsed', {}).get('usage') or {}
            if isinstance(usage.get('input_tokens'), int) and isinstance(usage.get('output_tokens'), int):
                input_tokens += usage['input_tokens']
                output_tokens += usage['output_tokens']
                usage_records += 1
        lines.append(f"| {config} | {report['logical_requests']} | " +
                     ', '.join(f'{k}: {v}' for k, v in sorted(statuses.items())) + ' | ' +
                     (f'{input_tokens:,} / {output_tokens:,}' if usage_records else 'Not reported') +
                     f' | {usage_records}/{report["logical_requests"]} |')
    lines += ['', 'Token totals above are provider/runtime-reported confirmation usage, not dollar proxies. '
        'Missing failure usage is unknown, not zero; tokenizers and interfaces differ. Subscription Astra '
        'has zero incremental metered API charge despite its actual calls and token processing. '
        'ProtectAI uses overlapping detector windows rather than generated output tokens.', '',
        'Failures and exact-0.5 abstentions are retained. Native 0.5 forecasts enter proper '
        'scoring; Boolean chat outputs have no invented probabilities. Continuations skip failed cells '
        'and process only unattempted jobs under the saved runtime amendments.', '',
        '## Paired authentic-task effects', '',
        'Each original task receives equal weight within its source. Entries are task minus candidate: '
        '**negative favors task context**. Decision error is in percentage points; Brier loss is in '
        'squared-probability units. Brackets show conditional 95% crossed-bootstrap intervals '
        '(5,000 draws); pair counts are complete/planned. Intervals condition on released fixtures, '
        'fixed templates and model versions and are not multiplicity-adjusted discoveries. '
        'Zero-width intervals describe observed agreement, not proof of no population effect.']
    for config in CONFIGS[:-1]:
        lines += ['', '### ' + config, '', '| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |',
                  '|---|---|---|']
        for source in reports[config]['strata']:
            effects = {e['metric']: e for e in source['paired_effects'] if e['scope'] == 'full_collection'}
            lines.append('| ' + source['dataset'] + ' | ' + effect_cell(effects.get('error')) + ' | ' +
                         effect_cell(effects.get('brier')) + ' |')
    lines += ['', 'ProtectAI has candidate-only window-max scores and no task-context contrast. '
        'Absolute false-alarm/miss rates, accuracy bounds, native Brier/log losses and reliability-bin '
        'denominators remain in [source metrics](analysis/source-metrics.csv) and the per-model JSON files. '
        'An improvement can coexist with a high absolute miss rate. The [primary table](analysis/primary-effects.csv) '
        'also includes task/text sensitivity, group counts, leave-one-task-out ranges and all-planned missing-response bounds.', '',
        '## Controls, reliability and interpretation', '',
        'The 83 pairs for format/reminder/scrambled controls were selected before outcomes. '
        'Compare task and each comparator on that same subset. Scrambling preserves words and may preserve '
        'partial meaning; these are constructed information interventions on the original scenario, '
        'not authentic alternate tasks with newly established labels. '
        'See [all control contrasts](analysis/control-effects.csv) and '
        '[source-specific interpretation](../../docs/extension-v3/CONTROL-RESULTS.md).', '',
        'The [paired-effect figure](figures/completed-arm-effects.png) and source-specific reliability grids '
        'are generated from saved evidence. Brier improvement does not alone establish calibration; '
        'bin averages have no uncertainty bands. Specialist window maxima are scores, not calibrated '
        'probabilities. Single-class sources and public-fixture prevalence limit reliability interpretation. '
        'No thresholds or calibration parameters were fitted on confirmation outcomes.', '',
        '## Accounting and limitations', '',
        f"Conservative all-in metered accounting is ${closure['all_in_conservative_accounted_usd']['openai']:.7f} "
        f"OpenAI and ${closure['all_in_conservative_accounted_usd']['typesafe']:.9f} TypeSafe, including prior checks "
        'and studies. This is recorded usage/reservation accounting, not a newly verified balance or invoice. '
        'Subscription fees and local electricity are excluded. No purchases, recharge or paid-route fallback were used.', '',
        'The original pilot, completed study and PDF remain historical. Source labels, repeated documents, '
        'shared attack templates, few independent tasks in some strata, public-data exposure and '
        'possible pretraining contamination limit generalization. The narrow frozen credential-fixture '
        'filter misses some published simulated prose/serialized mentions; no post-outcome exclusion '
        'or relabeling was applied. No prevention or legitimate-task-completion result is claimed.', '',
        'Broader research needs remain unmet: this is not a collection of thousands of independent '
        'tasks, independently adjudicated benign semantic labels, diverse unseen attack templates, '
        'or real production interactions. The GitHub stratum has only three task groups; clean-only '
        'and attack-only strata cannot supply both error rates. The preserved sources did not justify '
        'filling a larger numerical quota with repetitions or invented context. These limits motivate '
        'a separately scoped future collection with additional independent tasks and human-reviewed '
        'label semantics, not more calls on these same fixtures.', '',
        'See the [protocol](../../docs/extension-v3/PROTOCOL-v3.0.md), '
        '[related-artifact comparison](../../docs/extension-v3/RESEARCH-COMPARISON.md), '
        '[backend audit](../../docs/extension-v3/BACKEND-AUDIT.md), '
        '[representative errors and label limits](../../docs/extension-v3/ERROR-REVIEW.md), '
        '[reproduction instructions](../../docs/extension-v3/REPRODUCE.md), and '
        '[completion audit](../../docs/extension-v3/COMPLETION-STATUS.md), and '
        '[prioritized next-run handoff](../../docs/extension-v3/NEXT-RUN.md).', '']
    target = OUT / 'report.md'
    target.write_text('\n'.join(lines))
    (OUT / 'report-inputs-v1.json').write_text(json.dumps({'inputs_sha256': inputs,
        'script_sha256': sha(Path(__file__)), 'report_sha256': sha(target)}, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'generated_from_closed_verified_evidence', 'report': str(target.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
