"""Offline cap reconciliation, byte reservation envelope and precision scenarios."""
import collections,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v5.prepare import ROOT,RAW,OUT,read
from scripts.study_v5.prompts import conditions,native_payload
from scripts.source_discovery.prepare_review import preserve_write,sha256

def reconcile():
 p=ROOT/'results/controls-v4/execution-closure-v1.json';c=json.loads(p.read_text());ledger=ROOT/'results/controls-v4/inference-ledger-v1.json';entries=json.loads(ledger.read_text())['entries']
 if sha256(ledger.read_bytes())!=c['ledger_sha256']:raise ValueError('Closure ledger mismatch')
 if c['pending_reservations'] or c['in_flight_records']:raise ValueError('Unresolved live reservations')
 totals={provider:c['prior_accounted_usd'][provider]+math.fsum(e['accounted_usd'] for e in entries if e['provider']==provider) for provider in ['openai','typesafe']}
 for provider in totals:
  if not math.isclose(totals[provider],c['all_in_conservative_accounted_usd'][provider],abs_tol=1e-12):raise ValueError('Accounting mismatch')
 return {'closure_sha256':sha256(p.read_bytes()),'ledger_sha256':sha256(ledger.read_bytes()),'prior_accounted_usd':totals,'caps_usd':c['provider_caps_usd'],'remaining_accounting_headroom_usd':{p:c['provider_caps_usd'][p]-v for p,v in totals.items()},'retained_unknown_usage_reservations':len(c['unknown_usage_reservations_retained']),'is_provider_balance':False}
def reservation(payload,rate):return 2*(len(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode())+4096)*rate/1e6

def main():
 rows=read(RAW/'grouped-review-v2.jsonl')+read(RAW/'scope-pairs.jsonl');acc=reconcile();by={}
 for split in ['development','confirmation']:
  part=[r for r in rows if r['split_proposal']==split];totals={}
  for config,provider,rate in [('jev_firstparty','typesafe',.042),('luna_decisions','openai',.10)]:
   pp=[native_payload(r,c,config) for r in part for c in conditions(r)];amount=math.fsum(reservation(p,rate) for p in pp)
   totals[provider]={'cells':len(pp),'full_envelope_usd':amount,'max_request_bytes':max(len(json.dumps(p,ensure_ascii=False).encode()) for p in pp)}
  by[split]={'rows':len(part),'native_paid':totals,'six_contextual_plus_specialist_cells':sum(len(conditions(r))*6+1 for r in part)}
 scenarios=[{'groups':g,'assumed_paired_discordance':q,'approx_95_half_width_pp':100*1.96*math.sqrt(q/g),'approx_80pct_power_detectable_delta_pp':100*(1.96+.84)*math.sqrt(q/g)} for g in [8,30,60,100,126] for q in [.1,.25,.5]]
 report={'version':'v5-offline-feasibility-1','accounting':acc,'new_inference_spend_usd':0,'by_split':by,'cost_definition':'2 * (serialized UTF-8 bytes + 4096) * base input rate / 1e6; no discounts; planning reservation proxy, not measured usage or mathematical tokenizer bound','incremental_working_envelope_usd':{p:sum(by[s]['native_paid'][p]['full_envelope_usd'] for s in by) for p in ['openai','typesafe']},'proposed_operational_limits_usd':{'development_per_provider':.50,'v5_per_provider_including_development_and_recovery':5},'prices_checked':'2026-10-30 official OpenAI Decisions guide and TypeSafe models/API; exclude paid Responses, premium tiers, long context; recheck before freeze','precision_scenarios':scenarios,'zero_false_positive_one_sided_95_upper_bound_27_benign':1-.05**(1/27),'limitations':['All proposed rows counted as an upper planning envelope, not admitted confirmation.','Actual final costs must use frozen route-specific tokenization and current price/cache terms.','Normal precision formulas are scenarios for independent group means; not a claimed achieved power calculation.','Small-group source arms are descriptive; no reliable low-FPR or domain-population claims.']}
 preserve_write(OUT/'feasibility.json',json.dumps(report,indent=2,sort_keys=True).encode()+b'\n',raw=False)
 print(json.dumps({k:report[k] for k in ['accounting','by_split','incremental_working_envelope_usd']}))
if __name__=='__main__':main()
