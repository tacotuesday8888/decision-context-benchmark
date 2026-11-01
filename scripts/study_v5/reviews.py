"""Validate external reviews; never manufacture independent or human review."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
ALLOWED={'violation','allowed','unclear','not_applicable'}
def validate(review,record):
 if review.get('verdict') not in ALLOWED:raise ValueError('Missing/invalid verdict')
 for k in ['reviewer_id','rationale','context_needed','task_relation','instruction_type','ambiguity']:
  if not review.get(k,'').strip():raise ValueError('Missing review field '+k)
 if review.get('reviewer_kind') not in ['agent','human']:raise ValueError('Reviewer provenance required')
 if review['reviewer_kind']=='agent' and not review.get('reviewer_model_version','').strip():raise ValueError('Agent model/version required')
 if review['verdict'] in ['violation','allowed']:
  span=review.get('evidence_span','')
  if not span.strip() or not any(span in (record.get(k) or '') for k in ['candidate','task','policy']):raise ValueError('Evidence span is not verbatim evidence')
 return review

def resolve(record,reviews,adjudication=None):
 if not reviews:return {'status':'pending','gold':None,'eligible':False}
 if record.get('upstream_label') not in [0,1,'safe','unsafe']:raise ValueError('Unknown source label')
 for r in reviews:validate(r,record)
 if len({r['reviewer_id'] for r in reviews})!=len(reviews):raise ValueError('Duplicate reviewer identity')
 if any(r['ambiguity'].strip().lower()!='none' for r in reviews):return {'status':'ambiguity_requires_resolution','gold':None,'eligible':False}
 verdicts={r['verdict'] for r in reviews};upstream='violation' if record['upstream_label'] in [1,'unsafe'] else 'allowed'
 if any(r.get('group_merge_ids','').strip() for r in reviews):return {'status':'group_review_required','gold':None,'eligible':False}
 if verdicts=={upstream}:
  return {'status':'agent_reviewed_source_agreement' if any(r['reviewer_kind']=='agent' for r in reviews) else 'human_reviewed_source_agreement','gold':int(upstream=='violation'),'eligible':True}
 if adjudication:
  validate(adjudication,record)
  if adjudication['reviewer_id'] in {r['reviewer_id'] for r in reviews}:raise ValueError('Adjudicator must be a distinct reviewer')
  if adjudication['ambiguity'].strip().lower()!='none' or adjudication.get('group_merge_ids','').strip():
   return {'status':'adjudication_unresolved','gold':None,'eligible':False}
  if adjudication['verdict'] in ['violation','allowed']:
   return {'status':'adjudicated_'+adjudication['reviewer_kind'],'gold':int(adjudication['verdict']=='violation'),'eligible':True}
 return {'status':'disagreement_or_unclear','gold':None,'eligible':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--mapping',type=Path,required=True);p.add_argument('--reviews',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
 from scripts.source_discovery.prepare_review import preserve_write,canonical_bytes
 records={r['review_id']:r for r in [json.loads(l) for l in args.mapping.read_text().splitlines()]};reviews={k:[] for k in records}
 for path in args.reviews:
  rows=list(csv.DictReader(path.open()));seen=set()
  for r in rows:
   rid=r['review_id']
   if rid not in records or rid in seen:raise ValueError('Unknown or duplicate review ID')
   seen.add(rid)
   if r.get('verdict'):reviews[rid].append(r)
 results=[{'review_id':k,'source_id':r['id'],'reviews':reviews[k],**resolve(r,reviews[k])} for k,r in records.items()]
 preserve_write(args.out,b''.join(canonical_bytes(r)+b'\n' for r in results))
 print(json.dumps({'reviewed':sum(bool(v) for v in reviews.values()),'label_eligible':sum(r['eligible'] for r in results),'note':'Label eligibility is not run readiness; grouping/exposure/coverage/freeze remain required.'}))
if __name__=='__main__':main()
