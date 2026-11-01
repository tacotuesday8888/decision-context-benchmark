"""Separately versioned follow-up accounting. Pure offline rules; no auth/network.

The root executor owns transport. Only two pinned routes exist here: project-OAuth
Sol and first-party Jev. Historical v7 is read-only and inherited exactly once.
Calls, stages, optional lanes and one five-hour window are frozen in one manifest.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import copy
import json
from pathlib import Path
import re

from scripts.study_v6.accounting import (AccountingError, BudgetExceeded, AlreadyDispatched,
    BudgetLedger as JournalStateMachine, amount, money, _requests)
from scripts.study_v7.budget import BudgetLedger as ReviewedLedger, policy as reviewed_policy
from scripts.study_v7.requests import canonical, digest

VERSION='subscription-followup-budget-1'
PRIOR_RECEIPT_SHA256='b5601c0cb6365f50ba40ad7ed48e35e16f6b13371c6a1b74b00cf20044655983'
PRIOR_JOURNAL_SHA256='1f1df34267511c35addba2591c1def6f4aae1a4d07387f657283b7f75944f3e8'
PRIOR={'openai':'38.71694205','typesafe':'7.77900912600000006'}
CAPS={'openai':PRIOR['openai'],'typesafe':'21.82758493400000006'}
AVAILABLE={'openai':'0','typesafe':'14.048575808'}
PRIOR_UNKNOWN={'openai':'1.9952816','typesafe':'0'}
WINDOW_SECONDS=18000
JEV_RATE=Decimal('0.042')
JEV_CONTEXT=32000
JEV_RESERVATION='0.001344'
PRICING_SOURCE='https://docs.typesafe.ai/models'
PRICING={'source':PRICING_SOURCE,'checked_date':'2026-11-01','jev_usd_per_million':str(JEV_RATE),
    'jev_full_context_tokens':JEV_CONTEXT,'jev_maximum_request_usd':JEV_RESERVATION,'output_free':True}
ROUTES={
 'sol_subscription':{'model':'gpt-6.1-sol','route':'subscription','credential_source':'existing_project_oauth',
    'endpoint':'https://api.openai.com/v1/responses','provider':None},
 'jev_firstparty':{'model':'jev-1.14.0','route':'api_key','credential_source':'TYPESAFE_API_KEY',
    'endpoint':'https://api.typesafe.ai/v1/systemone','provider':'typesafe'},
}
LANES={
 'sol_general':{'groups':None,'per_group':{'sol_subscription':10,'jev_firstparty':0},
    'stages':{'preflight':{'sol_subscription':10},'main':{'sol_subscription':4000},'repeat':{'sol_subscription':400}}},
 'blind_audit':{'groups':100,'per_group':{'sol_subscription':1,'jev_firstparty':0},
    'stages':{'audit':{'sol_subscription':100}}},
 'second_source':{'groups':100,'per_group':{'sol_subscription':8,'jev_firstparty':8},
    'stages':{'secondary':{'sol_subscription':800,'jev_firstparty':800}}},
 'isolated_agent':{'groups':12,'per_group':{'sol_subscription':4,'jev_firstparty':2},
    'stages':{'actor':{'sol_subscription':48},'gate':{'jev_firstparty':24}}},
}


def _sha(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def route_for(config):
    if config not in ROUTES:raise AccountingError('Unapproved model/route; OpenAI API-key fallback is forbidden')
    return dict(ROUTES[config])


def validate_route(config, *, route, credential_source, endpoint):
    expected=route_for(config)
    if (route,credential_source,endpoint)!=(expected['route'],expected['credential_source'],expected['endpoint']):
        raise AccountingError('Route/auth source/endpoint differs; no paid OpenAI or fallback')
    return expected


def maximum_cost(config):
    route_for(config)
    return '0' if config=='sol_subscription' else JEV_RESERVATION


def usage_cost(config,usage):
    route_for(config)
    if config=='sol_subscription':return '0'
    n=usage.get('input_tokens') if isinstance(usage,dict) else None
    return amount(Decimal(n)*JEV_RATE/Decimal(1000000)) if type(n) is int and 0<n<=JEV_CONTEXT else None


def _batch(policy,lane,group_id,batch_id):
    if lane not in LANES or not isinstance(group_id,str) or not group_id or len(group_id)>256 or not isinstance(batch_id,str) or not batch_id:
        raise AccountingError('Named lane and stable bounded group/batch identity required')
    return canonical([VERSION,policy['manifest_sha256'],lane,group_id,batch_id]).decode()


def _unbatch(policy,value):
    try:version,sha,lane,group_id,batch_id=json.loads(value)
    except (ValueError,TypeError):raise AccountingError('Invalid follow-up batch namespace') from None
    if version!=VERSION or sha!=policy['manifest_sha256'] or value!=_batch(policy,lane,group_id,batch_id):
        raise AccountingError('Batch does not bind this frozen manifest/lane')
    return lane,group_id,batch_id


def request_spec(policy, *, lane, group_id, batch_id, stage, cell_id, config, payload):
    if not isinstance(cell_id,str) or not cell_id or len(cell_id)>256:raise AccountingError('Stable bounded cell identity required')
    route=route_for(config)
    if payload.get('model')!=route['model']:raise AccountingError('Pinned model changed')
    if config=='jev_firstparty' and (set(payload)!={'model','state','questions'} or not isinstance(payload.get('questions'),dict) or len(payload['questions'])!=1):
        raise AccountingError('Jev full32k ceiling requires exactly one question and default context')
    batch=_batch(policy,lane,group_id,batch_id);sha=digest(canonical(payload))
    key=digest(canonical([VERSION,policy['run_namespace'],batch,stage,cell_id,config,sha]))
    return {'key':key,'provider':route['provider'],'reserved_usd':maximum_cost(config),
        'request_sha256':sha,'config':config,'split':stage,'cell_id':cell_id}


def _specs(requests):
    requests=list(requests)
    rows=_requests([{k:v for k,v in r.items() if k!='cell_id'} for r in requests])
    for row,original in zip(rows,requests):
        cell=original.get('cell_id')
        if not isinstance(cell,str) or not cell or len(cell)>256:raise AccountingError('Stable bounded cell identity required')
        row['cell_id']=cell
    return rows


def _rules(manifest):
    declared=manifest.get('lanes')
    if not isinstance(declared,dict) or set(declared)!=set(LANES):raise AccountingError('Freeze exactly the four named lanes')
    result={}
    for lane,limits in LANES.items():
        value=declared[lane]
        if not isinstance(value,dict) or type(value.get('enabled')) is not bool:raise AccountingError('Every lane needs an explicit enabled flag')
        if lane=='isolated_agent' and value['enabled'] and (value.get('pilot_ready') is not True or not _sha(value.get('pilot_receipt_sha256'))):
            raise AccountingError('Isolated agent lane is disabled until a separate frozen pilot is ready')
        result[lane]={'enabled':value['enabled'],'limits':copy.deepcopy(limits),
            'pilot_receipt_sha256':value.get('pilot_receipt_sha256') if lane=='isolated_agent' else None}
    return result


def freeze_policy(manifest_path, *, prior_receipt_path, prior_journal_path):
    """Read/bind exact files; never write old evidence or invoke credentials/models."""
    manifest_path,prior_receipt_path,prior_journal_path=map(lambda x:Path(x).resolve(),(manifest_path,prior_receipt_path,prior_journal_path))
    manifest_bytes=manifest_path.read_bytes();manifest=json.loads(manifest_bytes)
    namespace=manifest.get('run_namespace')
    if not isinstance(namespace,str) or re.fullmatch(r'subscription-followup-[A-Za-z0-9_.-]+',namespace) is None:
        raise AccountingError('A new subscription-followup run namespace is required')
    if digest(prior_receipt_path.read_bytes())!=PRIOR_RECEIPT_SHA256 or digest(prior_journal_path.read_bytes())!=PRIOR_JOURNAL_SHA256:
        raise AccountingError('Closed v7 receipt/journal no longer match the immutable prior')
    receipt=json.loads(prior_receipt_path.read_text())
    if (receipt['accounting']['cumulative_conservative_accounted_usd']!=PRIOR or
        receipt['accounting']['unknown_v7_full_holds_usd']!=PRIOR_UNKNOWN or
        receipt['journal']['sha256']!=PRIOR_JOURNAL_SHA256 or not receipt['journal']['no_reserved_or_dispatched_entries']):
        raise AccountingError('Historical totals/unknown holds must be preserved without rebasing')
    routes=manifest.get('routes')
    if routes!=ROUTES:raise AccountingError('Manifest must pin only project-OAuth Sol and first-party Jev routes')
    lanes=_rules(manifest)
    allocations={lane:{'openai':'0','typesafe':amount(Decimal(sum(v.get('jev_firstparty',0) for v in item['limits']['stages'].values()))*Decimal(JEV_RESERVATION)) if item['enabled'] else '0'} for lane,item in lanes.items()}
    p=reviewed_policy(PRIOR,CAPS,AVAILABLE,allocations)
    p.update(version=VERSION,run_namespace=namespace,manifest_path=str(manifest_path),manifest_sha256=digest(manifest_bytes),
        routes=copy.deepcopy(ROUTES),lanes=lanes,window_seconds=WINDOW_SECONDS,
        prior_unknown_holds_usd=copy.deepcopy(PRIOR_UNKNOWN),prior_receipt_path=str(prior_receipt_path),prior_receipt_sha256=PRIOR_RECEIPT_SHA256,
        prior_journal_path=str(prior_journal_path),prior_journal_sha256=PRIOR_JOURNAL_SHA256,
        pricing=copy.deepcopy(PRICING))
    _validate_policy(p)
    return p


def _validate_policy(p):
    if (p.get('version')!=VERSION or p.get('prior_accounted_usd')!=PRIOR or p.get('provider_caps_usd')!=CAPS or
            p.get('incremental_caps_usd')!=AVAILABLE or p.get('v6_caps_usd')!=AVAILABLE or p.get('routes')!=ROUTES or
            p.get('prior_unknown_holds_usd')!=PRIOR_UNKNOWN or p.get('window_seconds')!=WINDOW_SECONDS or
            p.get('prior_receipt_sha256')!=PRIOR_RECEIPT_SHA256 or p.get('prior_journal_sha256')!=PRIOR_JOURNAL_SHA256 or
            not _sha(p.get('manifest_sha256')) or p.get('pricing')!=PRICING or
            not isinstance(p.get('run_namespace'),str) or re.fullmatch(r'subscription-followup-[A-Za-z0-9_.-]+',p['run_namespace']) is None):raise AccountingError('Frozen budget cannot raise caps/reset prior/enable paid OpenAI')
    declared={lane:{'enabled':item['enabled'],'pilot_ready':item['enabled'],
        'pilot_receipt_sha256':item.get('pilot_receipt_sha256')} for lane,item in p['lanes'].items()}
    if _rules({'lanes':declared})!=p['lanes']:raise AccountingError('Frozen lane limits changed')
    expected={lane:{'openai':'0','typesafe':amount(Decimal(sum(v.get('jev_firstparty',0) for v in item['limits']['stages'].values()))*Decimal(JEV_RESERVATION)) if item['enabled'] else '0'} for lane,item in p['lanes'].items()}
    if p['allocations_usd']!=expected:raise AccountingError('Named lane dollar caps changed')


def _validate_specs(state,batch_id,requests):
    p=state['policy'];lane,group,_=_unbatch(p,batch_id);rule=p['lanes'][lane]
    if not rule['enabled']:raise AccountingError('Lane is disabled in the frozen manifest')
    new=[]
    for r in requests:
        config=r.get('config');route=route_for(config);stage=r.get('split')
        if (stage not in rule['limits']['stages'] or config not in rule['limits']['stages'][stage] or
                r['provider']!=route['provider'] or money(r['reserved_usd'])!=money(maximum_cost(config))):
            raise AccountingError('Request route/stage/provider/full-context ceiling is not authorized')
        expected=digest(canonical([VERSION,p['run_namespace'],batch_id,stage,r['cell_id'],config,r['request_sha256']]))
        if r['key']!=expected:raise AccountingError('Request key lacks exact manifest/lane/batch/payload binding')
        old=state['entries'].get(r['key'])
        if old is None:new.append(r)
        elif any(old.get(k)!=v for k,v in r.items()):raise AccountingError('Retained request identity changed')
    cell_keys={(e['split'],e['config'],e['cell_id']):e['key'] for e in state['entries'].values() if e['allocation']==lane}
    for r in new:
        cell=(r['split'],r['config'],r['cell_id'])
        if cell in cell_keys:raise AccountingError('A preserved scientific cell cannot be retried/replaced in another batch')
        cell_keys[cell]=r['key']
    stage_counts=Counter((e['split'],e['config']) for e in state['entries'].values() if e['allocation']==lane)
    stage_counts.update((r['split'],r['config']) for r in new)
    for (stage,config),n in stage_counts.items():
        if n>rule['limits']['stages'][stage][config]:raise BudgetExceeded('Frozen per-stage call cap reached')
    group_counts=Counter();groups=set()
    for value in state['batches'].values():
        owner,g,_=_unbatch(p,value['batch_id'])
        if owner==lane:
            groups.add(g)
            if g==group:
                group_counts.update(state['entries'][key]['config'] for key in value['request_keys'])
    group_counts.update(r['config'] for r in new);groups.add(group)
    if rule['limits']['groups'] is not None and len(groups)>rule['limits']['groups']:raise BudgetExceeded('Frozen group cap reached')
    if any(n>rule['limits']['per_group'].get(c,0) for c,n in group_counts.items()):raise BudgetExceeded('Frozen per-group call cap reached')
    return lane


class FollowupLedger(ReviewedLedger):
    def __init__(self,path,frozen_policy=None,*,guard=None,clock=None):
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        if frozen_policy is not None:
            _validate_policy(frozen_policy)
            if Path(path).resolve()==Path(frozen_policy['prior_journal_path']).resolve() or {'study-v6','study-v7'} & set(Path(path).parts):
                raise AccountingError('Closed v7 must never be opened for follow-up writes')
        super().__init__(path,frozen_policy,guard=guard)
    @staticmethod
    def _apply(state,kind,data):
        if state is None:
            if kind!='initialize':raise AccountingError('Missing follow-up initialization')
            _validate_policy(data['policy'])
            return {'policy':data['policy'],'entries':{},'batches':{},'schedules':{},'continuations':{},
                'development_amendments':{},'window_started_at_utc':None,'last_dispatch_at_utc':None}
        if kind=='followup_start':
            if state['window_started_at_utc'] is not None:raise AccountingError('Five-hour clock cannot reset')
            _utc(data['at_utc']);state['window_started_at_utc']=data['at_utc'];return state
        if kind=='reserve':_validate_specs(state,data['batch_id'],data['new_requests'])
        elif kind=='dispatch':
            now=_utc(data['at_utc']);start=_utc(state['window_started_at_utc'])
            if now<start or now>=start+timedelta(seconds=WINDOW_SECONDS) or (state['last_dispatch_at_utc'] and now<_utc(state['last_dispatch_at_utc'])):
                raise AccountingError('Dispatch is outside the one frozen five-hour window')
            state['last_dispatch_at_utc']=data['at_utc']
        elif kind not in ('settle','cancel_reserved'):raise AccountingError('Unsupported follow-up journal event; no implicit amendments')
        return JournalStateMachine._apply(state,kind,data)
    def _check_guard(self,state):
        p=state['policy']
        for path,sha in ((p['manifest_path'],p['manifest_sha256']),(p['prior_receipt_path'],p['prior_receipt_sha256']),
                         (p['prior_journal_path'],p['prior_journal_sha256'])):
            self.verify_historical_file(path,sha)
        if self.guard is not None:self.guard()
    def _now(self):
        value=self.clock()
        if not isinstance(value,datetime) or value.tzinfo is None:raise AccountingError('Clock must be timezone-aware UTC')
        return value.astimezone(timezone.utc)
    def reserve_group(self,lane,group_id,requests,*,batch_id=None):
        self.verify_full_journal();rows=_specs(requests)
        with self._locked() as state:
            self._check_guard(state);now=self._now()
            if state['window_started_at_utc'] and now>=_utc(state['window_started_at_utc'])+timedelta(seconds=WINDOW_SECONDS):raise BudgetExceeded('Five-hour admission window ended')
            identity=_batch(state['policy'],lane,group_id,batch_id or group_id)
            _validate_specs(state,identity,rows)
            return self._reserve(state,identity,lane,rows)
    def mark_dispatched(self,key):
        with self._locked() as state:
            self._check_guard(state)
            if state['entries'][key]['status']!='reserved':raise AlreadyDispatched('Preserved intent/terminal attempt must never be resent')
            now=self._now();literal=now.isoformat()
            if state['window_started_at_utc'] is None:state=self._append(state,'followup_start',{'at_utc':literal})
            start=_utc(state['window_started_at_utc'])
            if now<start or now>=start+timedelta(seconds=WINDOW_SECONDS) or(state['last_dispatch_at_utc'] and now<_utc(state['last_dispatch_at_utc'])):raise BudgetExceeded('Frozen inference window expired or clock moved backwards')
            return dict(self._append(state,'dispatch',{'key':key,'at_utc':literal})['entries'][key])
    def settle(self,key,actual_usd=None,*,evidence_sha256=None):
        if not _sha(evidence_sha256):raise AccountingError('Settlement must bind immutable completion/raw evidence')
        actual=None if actual_usd is None else amount(actual_usd)
        with self._locked() as state:
            self._check_guard(state);entry=state['entries'][key]
            if actual is not None and money(actual)>money(entry['reserved_usd']):raise AccountingError('Usage exceeds reservation; retain full hold')
            if entry['status'] in ('settled','unknown_usage'):
                if entry['actual_usd']!=actual or entry['evidence_sha256']!=evidence_sha256:raise AccountingError('Terminal accounting evidence is immutable')
                return dict(entry)
            if entry['status']!='dispatched':raise AccountingError('No durable dispatch intent for settlement')
            return dict(self._append(state,'settle',{'key':key,'actual_usd':actual,'evidence_sha256':evidence_sha256})['entries'][key])
    def cancel_reserved(self,key,evidence_sha256):
        if not _sha(evidence_sha256):raise AccountingError('Unsent cancellation requires immutable evidence')
        with self._locked() as state:
            self._check_guard(state);entry=state['entries'][key]
            if entry['status']=='cancelled_unsent':
                if entry['evidence_sha256']!=evidence_sha256:raise AccountingError('Unsent cancellation evidence is immutable')
                return dict(entry)
            if entry['status']!='reserved':raise AccountingError('Cannot cancel any preserved dispatch intent')
            return dict(self._append(state,'cancel_reserved',{'key':key,'evidence_sha256':evidence_sha256,
                'reason':'positively_not_dispatched_after_execution_stop'})['entries'][key])
    def remaining_seconds(self):
        with self._locked() as state:
            if state['window_started_at_utc'] is None:return WINDOW_SECONDS
            return max(0.,(_utc(state['window_started_at_utc'])+timedelta(seconds=WINDOW_SECONDS)-self._now()).total_seconds())
    def register_schedule(self,*args,**kwargs):raise AccountingError('Use frozen named reserve_group API')
    def reserve_next_group(self,*args,**kwargs):raise AccountingError('Use frozen named reserve_group API')
    def reserve_batch(self,*args,**kwargs):raise AccountingError('Use frozen named reserve_group API')
    def reserve_unmetered_batch(self,*args,**kwargs):raise AccountingError('Use frozen named reserve_group API')
    def supersede_subscription_development(self,*args,**kwargs):raise AccountingError('No old-study supersession in the new ledger')


def _utc(value):
    if not isinstance(value,str):raise AccountingError('Missing durable UTC timestamp')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise AccountingError('Timestamp lacks timezone')
    return result.astimezone(timezone.utc)
