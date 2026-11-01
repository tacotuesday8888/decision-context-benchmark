"""Existing Laya tokenizer/SDK sequence audit; no inference or network access."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.study_v5.prepare import RAW,OUT,read
from scripts.study_v5.prompts import conditions,native_payload
from scripts.source_discovery.prepare_review import preserve_write,canonical_bytes,sha256
sys.path.insert(0,str(ROOT/'scripts/laya_v2'))
from adapter import LocalDecision

def main():
 runtime=LocalDecision();rows=read(RAW/'grouped-review-v2.jsonl')+read(RAW/'scope-pairs.jsonl');records=[]
 for r in rows:
  for c in conditions(r):
   p=native_payload(r,c,'laya_local');audit=runtime.audit(p);records.append({'id':r['id'],'condition':c,'payload_sha256':sha256(canonical_bytes(p)),**audit})
 body=b''.join(canonical_bytes(r)+b'\n' for r in records);preserve_write(RAW/'token-audit.jsonl',body)
 summary={'audited_payloads':len(records),'model_forward_passes':0,'max_input_tokens':max(r['input_tokens'] for r in records),'max_head_tokens':max(r['head_tokens'] for r in records),'truncated_payloads':sum(bool(r['truncated']) for r in records),'state_tokens_dropped':sum(r['state_tokens_dropped'] for r in records),'audit_sha256':sha256(body),'scope':'Laya exact local SDK sequence only; other routes need their own coverage checks before freeze.'}
 preserve_write(OUT/'token-audit.json',json.dumps(summary,indent=2).encode()+b'\n',raw=False);print(json.dumps(summary))
if __name__=='__main__':main()
