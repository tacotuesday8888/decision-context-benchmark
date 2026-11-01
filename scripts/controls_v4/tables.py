"""Source-specific denominators, token counts and observable prediction transitions."""
import csv,json
from collections import defaultdict
from pathlib import Path
import analyze
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
CONFIGS=['jev_firstparty','luna_decisions','laya_local','nimble_local','luna_chat','astra_chat','protectai_local']
def write(path,rows):
    with path.open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
def main():
    absolute=[];effects=[];resources=[];transitions=[]
    for config in CONFIGS:
        path=OUT/'analysis'/(config+'.json')
        if not path.exists():continue
        report=json.loads(path.read_text());rows=analyze.collect(config)
        for source in report['strata']:
            for condition in source['conditions']:
                row={'config':config,'dataset':source['dataset'],**{k:v for k,v in condition.items() if k not in ('forecast','accuracy_bounds_all_planned')}}
                row.update(accuracy_lower=condition['accuracy_bounds_all_planned'][0],accuracy_upper=condition['accuracy_bounds_all_planned'][1],brier=condition['forecast']['brier'],log_loss=condition['forecast']['log_loss'],probability_denominator=condition['forecast']['n_forecasts'])
                absolute.append(row)
            for effect in source['paired_effects']:
                point=effect['primary_cluster_weighted'];ci=point['interval'] if point else None
                effects.append({'config':config,'dataset':source['dataset'],'scope':effect['scope'],'control':effect['left'],'metric':effect['metric'],'planned_pairs':effect['planned_pairs'],'complete_pairs':effect['complete_pairs'],'primary_cluster_estimate':point['estimate'] if point else None,'primary_clusters':point['primary_clusters'] if point else None,'secondary_clusters':point['second_axis_groups'] if point else None,'ci_lower':ci[0] if ci else None,'ci_upper':ci[1] if ci else None,'equal_task_estimate':effect['equal_task_estimate'],'equal_text_estimate':effect['text_weighted_estimate'],'all_planned_lower':effect['all_planned_primary_cluster_weighted_bounds'][0],'all_planned_upper':effect['all_planned_primary_cluster_weighted_bounds'][1]})
        grouped=defaultdict(list)
        for r in rows:grouped[(r['dataset'],r['condition'])].append(r)
        for (source,condition),part in sorted(grouped.items()):
            incoming=[];outgoing=[]
            for r in part:
                raw=json.loads((ROOT/r['record_path']).read_text());parsed=raw.get('parsed',{});usage=parsed.get('usage',{})
                value=usage.get('input_tokens',parsed.get('input_tokens'))
                if type(value) is int:incoming.append(value)
                value=usage.get('output_tokens')
                if type(value) is int:outgoing.append(value)
            resources.append({'config':config,'dataset':source,'condition':condition,'planned_requests':len(part),'input_usage_records':len(incoming),'sum_input_tokens':sum(incoming),'mean_input_tokens':sum(incoming)/len(incoming) if incoming else None,'max_input_tokens':max(incoming) if incoming else None,'output_usage_records':len(outgoing),'sum_output_tokens':sum(outgoing),'sum_route_seconds':sum(r['elapsed_seconds'] for r in part),'conservative_accounted_usd':sum(r['conservative_accounted_usd'] for r in part),'latency_scope':'Observed route time with concurrent routes; not intrinsic model speed'})
        if config=='protectai_local':continue
        lookup={(r['id'],r['condition']):r for r in rows}
        for source in sorted({r['dataset'] for r in rows}):
            ids=sorted({r['id'] for r in rows if r['dataset']==source})
            for control in ['reminder','format','candidate','scrambled']:
                counts=defaultdict(list)
                for identity in ids:
                    a,b=lookup[(identity,control)],lookup[(identity,'task')]
                    if not a['valid'] or not b['valid']:label='incomplete_or_abstained'
                    elif a['prediction']==b['prediction']:label='unchanged_correct' if b['prediction']==b['gold'] else 'unchanged_wrong'
                    elif b['prediction']==b['gold']:label='corrected_missed_attack' if b['gold'] else 'corrected_false_alarm'
                    else:label='created_missed_attack' if b['gold'] else 'created_false_alarm'
                    counts[label].append(identity)
                for label,identities in sorted(counts.items()):
                    transitions.append({'config':config,'dataset':source,'control':control,'transition':label,'count':len(identities),'first_three_ids':';'.join(identities[:3]),'scope':'Observed output transition; example ordering fixed by ID, not explanation or narrative appeal'})
    target=OUT/'tables';target.mkdir(exist_ok=True)
    for name,rows in [('absolute',absolute),('effects',effects),('resources',resources),('transitions',transitions)]:
        if rows:write(target/(name+'.csv'),rows)
    print(json.dumps({'completed_configs':len({r['config'] for r in absolute}),'absolute_rows':len(absolute),'effect_rows':len(effects)}))
if __name__=='__main__':main()
