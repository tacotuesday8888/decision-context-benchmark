"""Final source-specific numerical readout; refuses incomplete experiment closure."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
CONFIGS=['jev_firstparty','luna_decisions','laya_local','nimble_local','luna_chat','astra_chat','protectai_local']
NAMES={'jev_firstparty':'Jev 1.14','luna_decisions':'Luna Decisions','laya_local':'Laya','nimble_local':'Nimble','luna_chat':'Luna chat','astra_chat':'Astra chat','protectai_local':'ProtectAI'}
def percent(value):return '—' if value is None else f'{100*value:.2f}'
def contrast(effect):
    p=effect['primary_cluster_weighted']
    if not p:return 'No complete pairs'
    ci=p['interval'];interval=f'[{100*ci[0]:.2f}, {100*ci[1]:.2f}]' if ci else '[insufficient groups]'
    return f"{100*p['estimate']:+.2f} {interval}; {effect['complete_pairs']}/{effect['planned_pairs']}"
def main():
    closure=json.loads((OUT/'execution-closure-v1.json').read_text());assert closure['status']=='terminal'
    reports={};hashes={}
    for config in CONFIGS:
        p=OUT/'analysis'/(config+'.json');digest=hashlib.sha256(p.read_bytes()).hexdigest()
        for suffix in ['-verification.json','-bootstrap-verification.json']:
            receipt=json.loads((OUT/'analysis'/(config+suffix)).read_text());assert receipt['status']=='passed' and receipt['analysis_sha256']==digest
        audit=json.loads((OUT/'analysis'/(config+'-record-audit.json')).read_text());assert audit['status']=='passed'
        reports[config]=json.loads(p.read_text());hashes[config]=digest
    lines=['# Decision Context Benchmark: full controls v4', '',
        'The full five-condition experiment is complete. Results below measure agreement with published construction/control labels; independently reviewed semantic labels remain unassigned. Detection is not evidence that an agent would resist an attack.', '',
        'The main source has 408 matched clean/attack examples from 204 QA tasks and 27 articles. The supplemental source has 17 community-authored synthetic fixtures, including only three benign controls. These sources are reported separately. Neither source establishes broad real-world domain transfer or performance on near-target corruption.', '',
        'Each contextual configuration received all five conditions on all 425 examples. ProtectAI received candidate-only inputs. There are seven configurations but six model IDs; the two Luna interfaces are not independent model families. Prompts, thresholds and settings were frozen before confirmation.', '',
        'Central contrasts below are control error minus authentic-task error: positive favors the task. Intervals are pointwise 95% crossed bootstrap intervals, conditional on the released source and fixed broad attack family. QA uses equal article weights; AIB uses equal task weights. Zero or boundary intervals are not proof of population equivalence. Complete/planned paired denominators are shown.', '']
    for source,title in [('tasktracker-qa-advbench','TaskTracker QA / AdvBench'),('aib-static-stress','AIB supplemental static fixtures')]:
        lines += ['## '+title,'','| Configuration | Task vs reminder (pp), interval; pairs | Task vs empty field (pp), interval; pairs | Task vs scrambled (pp), interval; pairs |','|---|---|---|---|']
        for config in CONFIGS[:-1]:
            s=next(s for s in reports[config]['strata'] if s['dataset']==source)
            items={e['left']:e for e in s['paired_effects'] if e['scope']=='all_confirmation' and e['metric']=='error'}
            lines.append('| '+NAMES[config]+' | '+' | '.join(contrast(items[c]) for c in ['reminder','format','scrambled'])+' |')
        lines += ['', 'Absolute valid-response error rates are per text, not article weighted. Candidate-only and task rates are shown together so improvements are not mistaken for low error.', '', '| Configuration | Candidate FPR / FNR (%) | Task FPR / FNR (%) | Candidate valid / planned | Task valid / planned |','|---|---|---|---|---|']
        for config in CONFIGS:
            s=next(s for s in reports[config]['strata'] if s['dataset']==source);cs={c['condition']:c for c in s['conditions']};a=cs['candidate'];b=cs.get('task')
            lines.append(f"| {NAMES[config]} | {percent(a['fpr'])} / {percent(a['fnr'])} | "+(f"{percent(b['fpr'])} / {percent(b['fnr'])}" if b else 'unsupported')+f" | {a['valid']}/{a['planned']} | "+(f"{b['valid']}/{b['planned']}" if b else '—')+' |')
        lines += ['','Native probability Brier/log losses, all-planned missingness bounds, error-direction contrasts, equal-task/text sensitivities, token counts and observed transitions are retained in `results/controls-v4/tables/` and the full analysis JSON. No chat probabilities were invented.','']
    totals=closure['all_in_conservative_accounted_usd']
    lines += ['## Execution and interpretation limits','',f"All {closure['planned_cells_including_development']:,} frozen development and confirmation cells are terminal. Unknown-usage reservations retained: {len(closure['unknown_usage_reservations_retained'])}. Cumulative conservative accounting, including earlier studies: OpenAI ${totals['openai']:.6f} / $15; TypeSafe ${totals['typesafe']:.6f} / $20. These are usage/reservation records, not refreshed account balances or invoices.",'',
        'Provider errors, truncations, refusals, ties and semantic disagreements remain distinct. Failed confirmation cells were not replaced. Development retained one Decisions 503 and an explicit Ollama runtime update to 0.40.13 with unchanged Nimble weights. The analysis-helper import collision was fixed before any Laya confirmation call. Details and hashes are retained in the amendment/startup receipts.', '',
        'Scrambling retains lexical clues and can retain meaning; token counts can change. The task-versus-scrambled contrast alone cannot isolate semantics. All prompts contain the same detector definition, so the reminder contrast tests additional reminder wording rather than a completely instruction-free detector.', '',
        'The main source is dominated by explicit distant-target diversions and ordinary encyclopedia paragraphs. The tiny supplemental source probes legitimate imperatives and authority claims but cannot supply a precise false-alarm estimate. Gold remains source construction status, not independent human semantic adjudication. Examples requiring missing trusted context or unresolved source alignment were quarantined; no post-outcome exclusions were made.', '',
        'See ERROR-REVIEW.md for exploratory output transitions, counterexamples and source limitations. Those observations do not infer internal reasoning. The next justified data work is an independently reviewed set of authentic task-relative benign instructions and near-target attacks with reliable provenance and held-out document/family groups. Calibration, fine-tuning and end-to-end prevention would be separate experiments.', '',
        'Independent arithmetic, explicit-multiplicity bootstrap and raw-request/parser/accounting checks passed for every configuration. Final isolated reproduction and repository CI are documented by their own receipts; this report does not replace those delivery checks.', '']
    (ROOT/'docs/controls-v4/RESULTS.md').write_text('\n'.join(lines))
    (OUT/'report-inputs-v1.json').write_text(json.dumps({'analysis_sha256':hashes,'closure_sha256':hashlib.sha256((OUT/'execution-closure-v1.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
