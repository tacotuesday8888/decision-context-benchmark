"""A separately frozen, bounded substitution for the unavailable Gemini 3.8 route."""
from datetime import datetime,timezone
import json
import time
from prepare_pilot import ROOT,sha
import run_pilot as base
from smoke_access import post,env_secret

OUT=ROOT/'results/pilot/gemini-3.7-records'
MODEL='gemini-3.7-flash'


def requests():
    original=[r for r in base.plan() if r['provider']=='gemini']
    # Changing the model family must never alter context, label, prompt or sample.
    return sorted(original,key=lambda r:(r['example']['split']!='dev',r['example']['id'],r['condition']))


def main():
    OUT.mkdir(exist_ok=True)
    protocol=ROOT/'docs/gemini-substitution.md'
    planned=requests()
    frozen={'model':MODEL,'protocol_sha256':sha(protocol.read_bytes()),
            'original_plan_sha256':sha((ROOT/'results/pilot/frozen-plan.json').read_bytes()),
            'requests':[{'id':r['example']['id'],'split':r['example']['split'],'condition':r['condition'],
                         'request_sha256':r['request_sha256']} for r in planned]}
    content=json.dumps(frozen,indent=2,sort_keys=True)+'\n'
    snapshot=ROOT/'results/pilot/gemini-3.7-plan.json'
    if snapshot.exists() and snapshot.read_text()!=content:raise ValueError('Substitution plan changed')
    snapshot.write_text(content)
    base.MODELS['gemini']=MODEL
    for r in planned:
        e=r['example'];key=sha('gemini-3.7'+e['id']+r['condition'])[:24];path=OUT/(key+'.json')
        if path.exists():continue
        previous=[json.loads(p.read_text()) for p in OUT.glob('*.json')]
        if any(x['status']!='ok' and (x['split']=='dev' or x['attempts'][-1]['http_status']!=200) for x in previous):
            print('Substitution paused after unsuccessful availability/development check.',flush=True);return
        if len(previous)>=20:print('Request cap reached.',flush=True);return
        if e['split']=='eval' and sum(x['split']=='dev' and x['status']=='ok' for x in previous)!=4:
            raise ValueError('Development completion required')
        time.sleep(13)
        headers={'x-goog-api-key':env_secret('GEMINI_API_KEY')}
        url='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent'
        started=datetime.now(timezone.utc).isoformat()
        obs,body=post(url,r['request'],headers)
        obs['attempt']=1;obs['raw_body']=base.scrub(body or '',headers)
        result={'run':'gemini-substitution','provider':'gemini-3.7','requested_model':MODEL,'endpoint':url,
                'id':e['id'],'gold':e['gold'],'group':e['group'],'split':e['split'],
                'condition':r['condition'],'candidate_sha256':e['candidate_sha256'],
                'request':r['request'],'request_sha256':r['request_sha256'],'started_at':started,
                'attempts':[obs],'paid_spend_usd':0,'prediction':None,'valid':False,'status':'http_error'}
        if obs['http_status']==200:
            try:
                result.update(base.parse_response('gemini',obs['raw_body']))
                result['status']='ok' if result['valid'] else 'invalid_or_abstention'
            except (ValueError,KeyError,TypeError) as error:
                result['status']='parse_or_version_error';result['error_type']=type(error).__name__
        path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({k:result.get(k) for k in ['provider','id','split','condition','status','prediction']}),flush=True)
        if result['status']!='ok' and (e['split']=='dev' or obs['http_status']!=200):return


if __name__=='__main__':main()
