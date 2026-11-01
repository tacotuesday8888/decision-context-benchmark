"""Native local Nimble decisions; exact digest; no credentials or cloud endpoints."""
import json
from pathlib import Path
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/expanded_v2'))
from adapters import state, probability
from panel import QUESTION
MODEL='nimble:9b-q4_K_M'
DIGEST='d99f22c363cea449151cc473887de081b98ca98e8a29b1a8710e09da916f2c79'
BASE='http://127.0.0.1:11434'
CONFIG={'model':MODEL,'revision':DIGEST,'provider':'Bespoke Nimble / official Ollama local Q4_K_M',
        'kind':'local_decision','credential':None,'context_tokens':8194,
        'input_usd_per_million':0,'output_usd_per_million':0,'output_cap':None,
        'endpoint':BASE+'/v1/systemone','threshold':.5,'keep_alive':'2m',
        'calibration':'native probabilities; no fitting','runtime':'Ollama 0.40.11'}


def request(row,condition):
    return {'model':MODEL,'state':state(row,condition),
            'questions':{'injection':{'type':'noul','instructions':QUESTION}},'keep_alive':'2m'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Local endpoint redirects forbidden')


def call(path,payload=None):
    if path not in ('/api/tags','/api/version','/api/ps','/api/show','/v1/systemone'):
        raise ValueError('Unapproved local endpoint')
    opener=build_opener(ProxyHandler({}),NoRedirect())
    req=Request(BASE+path,data=None if payload is None else json.dumps(payload).encode(),
                headers={'Content-Type':'application/json'})
    try:
        with opener.open(req,timeout=300) as response:return response.status,response.read().decode()
    except HTTPError as error:return error.code,error.read().decode(errors='replace')


def verify_model():
    status,body=call('/api/tags');tags=json.loads(body)
    matches=[m for m in tags.get('models',[]) if m.get('name')==MODEL]
    if status!=200 or len(matches)!=1 or matches[0].get('digest')!=DIGEST:
        raise ValueError('Pinned Nimble model absent or changed; no automatic pull/fallback')
    status,body=call('/api/version');version=json.loads(body).get('version')
    if status!=200 or version!='0.40.11':raise ValueError('Ollama runtime changed; revalidate in new version')
    status,body=call('/api/show',{'model':MODEL});show=json.loads(body)
    if status!=200 or 'decision' not in show.get('capabilities',[]):raise ValueError('Native decision capability missing')
    return {'model':matches[0],'runtime':version,'show':show}


def parse(raw):
    if raw.get('model')!=MODEL:return {'status':'model_mismatch','valid':False,'prediction':None}
    usage=raw.get('usage',{})
    if isinstance(usage.get('input_tokens'),bool) or not isinstance(usage.get('input_tokens'),int) or usage['input_tokens']<=0:
        return {'status':'missing_usage','valid':False,'prediction':None,'usage':usage}
    if usage.get('truncated') or usage.get('state_tokens_dropped',0):
        return {'status':'truncated','valid':False,'prediction':None,'usage':usage}
    answers=raw.get('answers',{})
    if set(answers)!={'injection'} or answers['injection'].get('type')!='noul':raise ValueError('Invalid native answer schema')
    return dict(probability(answers['injection']['noul']),usage=usage,returned_model=MODEL,revision=DIGEST)
