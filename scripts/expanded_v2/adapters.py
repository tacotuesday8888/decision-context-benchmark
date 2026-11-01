"""Offline payloads/parsers. Paid execution is deliberately disabled in this preparation."""
import json,math,sys
from common import ROOT
from panel import PANEL,QUESTION,SYSTEM
sys.path.insert(0,str(ROOT/'scripts'))
from response_metadata import terminal_metadata
from smoke_access import parse_openai_stream

SCHEMA={'type':'object','properties':{'injection':{'type':'boolean'}},'required':['injection'],'additionalProperties':False}


def state(row,condition):
    if condition not in row['conditions']:raise ValueError('Unsupported context condition')
    result={'CANDIDATE':row['candidate']}
    if condition in ['task','both']:result['TRUSTED_USER_TASK']=row['trusted_task']
    if condition in ['source','both']:
        result['UNTRUSTED_SOURCE_BEFORE']=row['surrounding_before'] or ''
        result['UNTRUSTED_SOURCE_AFTER']=row['surrounding_after'] or ''
    return json.dumps(result,ensure_ascii=False,sort_keys=True)


def request(config,row,condition):
    p=PANEL[config];evidence=state(row,condition)
    if p['kind']=='noul':return {'model':p['model'],'state':evidence,'questions':{'injection':{'type':'noul','instructions':QUESTION}}}
    if p['kind']=='predicate':return {'model':p['model'],'input':evidence,'questions':[{'name':'injection','type':'predicate','instructions':QUESTION}]}
    if p['kind']=='local_detector':
        if condition!='candidate':raise ValueError('Native specialist has no task-relative context interface')
        return {'model':p['model'],'revision':p['revision'],'candidate':row['candidate'],'window_tokens':p['window_tokens'],
                'overlap_tokens':p['overlap_tokens'],'aggregation':p['aggregation']}
    return {'model':p['model'],'instructions':SYSTEM,'input':[{'role':'user','content':evidence}],
            'store':False,'stream':True,'reasoning':{'effort':p['reasoning_effort']},'max_output_tokens':p['output_cap'],
            'text':{'format':{'type':'json_schema','name':'injection_decision','strict':True,'schema':SCHEMA}}}


def probability(value):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid score')
    return {'status':'tie' if value==.5 else 'ok','valid':value!=.5,'prediction':None if value==.5 else int(value>.5),'score':value}


def parse(config,body):
    p=PANEL[config]
    if p['kind']=='chat':
        meta=terminal_metadata('openai',body)
        # Incomplete, refused, interrupted and semantic errors are different states.
        if meta.get('termination')=='incomplete':
            reason=(meta.get('incomplete_details') or {}).get('reason')
            return dict(meta,status='truncated' if reason=='max_output_tokens' else 'provider_incomplete',valid=False,prediction=None)
        if meta.get('termination')=='failed':return dict(meta,status='provider_failed',valid=False,prediction=None)
        if meta.get('termination')!='completed':return dict(meta,status='interrupted_stream',valid=False,prediction=None)
        result=parse_openai_stream(body);response=result['response']
        if response.get('model')!=p['model']:return dict(meta,status='model_mismatch',valid=False,prediction=None)
        if any(c.get('type')=='refusal' for item in response.get('output',[]) for c in item.get('content',[])):
            return dict(meta,status='refusal',valid=False,prediction=None)
        try:
            answer=json.loads(result['stream_output_text'])
            if not isinstance(answer,dict) or set(answer)!={'injection'} or not isinstance(answer['injection'],bool):raise ValueError('Boolean required')
            return dict(meta,status='ok',valid=True,prediction=int(answer['injection']))
        except (ValueError,TypeError):return dict(meta,status='invalid_format',valid=False,prediction=None)
    result=json.loads(body)
    if result.get('model')!=p['model']:return {'status':'model_mismatch','valid':False,'prediction':None}
    if p['kind']=='noul':answer=probability(result['answers']['injection']['noul'])
    elif p['kind']=='predicate':
        matching=[a for a in result['answers'] if a.get('name')=='injection']
        if len(matching)!=1:raise ValueError('Missing or duplicate decision')
        if matching[0]['type']=='refusal':return {'status':'refusal','valid':False,'prediction':None}
        if matching[0]['type']!='predicate':raise ValueError('Wrong decision type')
        answer=probability(matching[0]['probability'])
    else:raise ValueError('Use local model adapter')
    answer.update({'returned_model':result['model'],'usage':result.get('usage',{})});return answer


def windows(ids,width=510,overlap=64):
    if not 0<=overlap<width:raise ValueError('Invalid overlap')
    for start in range(0,max(1,len(ids)),width-overlap):
        yield ids[start:start+width]
        if start+width>=len(ids):break


class LocalDetector:
    def __init__(self):
        import torch
        from transformers import AutoTokenizer,AutoModelForSequenceClassification
        p=PANEL['protectai_local'];self.torch=torch
        self.tokenizer=AutoTokenizer.from_pretrained(p['model'],revision=p['revision'],trust_remote_code=False,local_files_only=True)
        self.model=AutoModelForSequenceClassification.from_pretrained(p['model'],revision=p['revision'],trust_remote_code=False,local_files_only=True,use_safetensors=True).cpu().eval()
        if self.model.config.id2label.get(1)!='INJECTION':raise ValueError('Unexpected label mapping')
        torch.set_num_threads(2)

    def classify(self,text):
        scores=[];ids=self.tokenizer.encode(text,add_special_tokens=False)
        for chunk in windows(ids):
            encoded=self.tokenizer.prepare_for_model(chunk,add_special_tokens=True,return_tensors='pt',return_token_type_ids=False)
            encoded={k:(v.unsqueeze(0) if v.ndim==1 else v) for k,v in encoded.items()}
            if encoded['input_ids'].shape[1]>512:raise ValueError('Window exceeds model limit')
            with self.torch.inference_mode():scores.append(float(self.model(**encoded).logits.softmax(-1)[0,1]))
        return dict(probability(max(scores)),windows=len(scores),window_scores=scores,input_tokens=len(ids),
                    returned_model=PANEL['protectai_local']['model'],revision=PANEL['protectai_local']['revision'])


def paid_execute(*args,**kwargs):
    raise PermissionError('Paid requests and evaluation are disabled while billing is pending')
