"""Explicit, unsent-only core continuation; frozen v1 budget remains unchanged.

Pure metadata preparation/replay. No credential, response, auth or model is read.
A new ledger inherits the original clock and all prior actual call consumption.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timedelta
import copy
import json
from pathlib import Path

from scripts.subscription_followup import budget as base
from scripts.study_v7.requests import canonical,digest

ROOT=Path(__file__).resolve().parents[2]
VERSION='subscription-followup-core-continuation-1'
ORIGINAL_JOURNAL_SHA256='05cf42e643a72dc0d248f593d46fddcea41b40d5b81315f5c71dce2999420426'
ORIGINAL_START='2026-11-01T14:57:56.429131+00:00'
STAGE_CAPS={'preflight':10,'main':4000,'repeat':400,'audit':100}
BINDINGS={'original_manifest','original_stop','original_journal','original_snapshot','receipt'}


def _need(value,message):
    if not value:raise base.AccountingError(message)


def _path(value):
    path=Path(value);return path.resolve() if path.is_absolute() else (ROOT/path).resolve()


def _load(item):
    path=_path(item['path']);body=path.read_bytes()
    _need(digest(body)==item['sha256'],'Continuation binding bytes changed: '+str(path))
    return json.loads(body),{'path':str(path),'sha256':item['sha256']}


def _replay(item):
    path=_path(item['path']);body=path.read_bytes();_need(body.endswith(b'\n') and digest(body)==item['sha256'],'Closed core journal changed/torn')
    state=None;previous='0'*64
    for index,line in enumerate(body.splitlines()):
        event=json.loads(line);sha=event.pop('sha256',None)
        _need(event['index']==index and event['previous_sha256']==previous and sha==digest(canonical(event)),'Closed core journal chain changed')
        state=base.FollowupLedger._apply(state,event['kind'],event['data'])
        state['head_sha256'],state['events']=sha,index+1;previous=sha
    _need(state is not None and all(e['status'] in {'settled','unknown_usage','cancelled_unsent'} for e in state['entries'].values()),'Original core journal must be terminal')
    return state,{'path':str(path),'sha256':item['sha256']}


def _roster(plan):
    roster={};cells={}
    for group in plan['groups']:
        _need(group['lane'] in {'sol_general','blind_audit'},'Only the original core lanes may continue')
        _need(group['stage'] in STAGE_CAPS,'Unknown core stage')
        _need(group['lane']==('blind_audit' if group['stage']=='audit' else 'sol_general'),'Core stage/lane changed')
        for cell in group['cells']:
            cid=cell['cell_id'];_need(cid not in roster,'Duplicate logical cell in frozen roster')
            _need(cell['config']=='sol_subscription' and cell['group_id']==group['group_id'],'Continuation cannot alter route/group')
            _need(digest(canonical(cell['payload']))==cell['payload_sha256'],'Continuation payload hash differs')
            roster[cid]={'config':cell['config'],'stage':group['stage'],'group_id':group['group_id'],
                'lane':group['lane'],'payload_sha256':cell['payload_sha256']};cells[cid]=cell
    return roster,cells


def freeze_continuation_policy(manifest_path,*,prior_receipt_path,prior_journal_path):
    """Bind both terminal ancestor metadata and exact never-dispatched roster."""
    path=Path(manifest_path).resolve();manifest=json.loads(path.read_bytes())
    policy=base.freeze_policy(path,prior_receipt_path=prior_receipt_path,prior_journal_path=prior_journal_path)
    _need(not manifest['lanes']['second_source']['enabled'] and not manifest['lanes']['isolated_agent']['enabled'],'No extension lane in core continuation')
    c=manifest['continuation'];_need(c.get('version')==VERSION and set(c['bindings'])==BINDINGS,'Explicit original core lineage bindings required')
    originals=c['bindings'];bound={}
    old_manifest,bound['original_manifest']=_load(originals['original_manifest'])
    stop,bound['original_stop']=_load(originals['original_stop'])
    snapshot,bound['original_snapshot']=_load(originals['original_snapshot'])
    receipt,bound['receipt']=_load(originals['receipt'])
    _need(originals['original_journal']['sha256']==ORIGINAL_JOURNAL_SHA256,'Only the exact sealed original core journal can continue')
    state,bound['original_journal']=_replay(originals['original_journal'])
    original_manifest_sha=bound['original_manifest']['sha256']
    _need(stop.get('status')=='closed' and stop.get('manifest_sha256')==original_manifest_sha and stop.get('journal_sha256')==ORIGINAL_JOURNAL_SHA256,'Original STOP does not bind terminal core bytes')
    _need(state['policy']['manifest_sha256']==original_manifest_sha and snapshot.get('terminal') is True and
        snapshot['entries']==state['entries'] and snapshot['head_sha256']==state['head_sha256'] and snapshot['policy']==state['policy'],
        'Original final snapshot differs from terminal journal')
    _need(snapshot['all_in_accounted_usd']==base.PRIOR and all(base.money(e['accounted_usd'])==0 and e['provider'] is None and
        e['config']=='sol_subscription' for e in state['entries'].values()),'Original core must add no API dollars')
    start=state['window_started_at_utc'];_need(start==ORIGINAL_START,'Original first-inference clock differs')
    deadline=(base._utc(start)+timedelta(seconds=base.WINDOW_SECONDS)).isoformat()
    old_plan,bound['original_plan']=_load(old_manifest['plan']);new_plan,bound['new_plan']=_load(manifest['plan'])
    old_roster,old_cells=_roster(old_plan);allowed,new_cells=_roster(new_plan)
    _need(Counter(item['stage'] for item in old_roster.values())==STAGE_CAPS,'Original4510-cell stage scope changed')
    actual={};cancelled={}
    for key,entry in state['entries'].items():
        cid=entry['cell_id'];_need(cid in old_roster,'Ancestor entry outside original roster')
        g=old_roster[cid]
        _need(entry['config']==g['config'] and entry['split']==g['stage'] and entry['allocation']==g['lane'] and
            entry['request_sha256']==g['payload_sha256'],'Ancestor admitted scientific identity changed')
        spec=base.request_spec(state['policy'],lane=g['lane'],group_id=g['group_id'],batch_id=g['group_id'],
            stage=g['stage'],cell_id=cid,config=g['config'],payload=old_cells[cid]['payload'])
        _need(all(entry.get(k)==v for k,v in spec.items()),'Ancestor key/spec no longer matches original frozen cell')
        if entry['status']=='cancelled_unsent':
            _need(base.money(entry['actual_usd'])==0 and base.money(entry['accounted_usd'])==0 and base._sha(entry['evidence_sha256']),
                'Cancelled ancestor is not positively unsent/zero')
            cancelled[cid]={'key':key,'evidence_sha256':entry['evidence_sha256']}
        else:
            _need(cid not in actual,'Original logical cell was dispatched twice');actual[cid]=g['stage']
    _need(set(allowed)==set(old_roster)-set(actual),'Continuation must be exactly original never-dispatched cells; no failed-first replacement')
    for cid in allowed:
        _need(allowed[cid]==old_roster[cid] and canonical(new_cells[cid])==canonical(old_cells[cid]),'Unsent scientific cell/payload was changed')
    prior_counts={stage:sum(s==stage for s in actual.values()) for stage in STAGE_CAPS}
    remaining_counts={stage:sum(s['stage']==stage for s in allowed.values()) for stage in STAGE_CAPS}
    _need(prior_counts['preflight']==10 and remaining_counts['preflight']==0,'Preflight cannot repeat in continuation')
    checks={'version':VERSION,'original_manifest_sha256':original_manifest_sha,
        'original_stop_sha256':bound['original_stop']['sha256'],'original_journal_sha256':ORIGINAL_JOURNAL_SHA256,
        'original_snapshot_sha256':bound['original_snapshot']['sha256'],'original_plan_sha256':bound['original_plan']['sha256'],
        'new_plan_sha256':bound['new_plan']['sha256'],'prior_actual_stage_counts':prior_counts,
        'prior_actual_cells':len(actual),'proven_unsent_cancelled_cells':len(cancelled),
        'never_admitted_cells':len(old_roster)-len(state['entries']),'remaining_cells':len(allowed),
        'original_window_started_at_utc':start,'original_deadline_utc':deadline,
        'continuation_cell_ids_sha256':digest(canonical(sorted(allowed))),'never_retry_dispatched':True}
    _need(all(receipt.get(k)==v for k,v in checks.items()),'Continuation receipt does not match independently derived original scope/clock/unsent proof')
    policy['continuation']={'version':VERSION,'bindings':bound,'allowed_roster':allowed,
        'allowed_roster_sha256':digest(canonical(allowed)),'prior_actual_cell_ids':sorted(actual),
        'prior_actual_stage_counts':prior_counts,'cancelled_unsent_ancestor':cancelled,
        'original_window_started_at_utc':start,'original_deadline_utc':deadline,
        'original_last_dispatch_at_utc':state['last_dispatch_at_utc']}
    _validate(policy)
    return policy


def _validate(policy):
    base._validate_policy(policy);c=policy.get('continuation',{})
    _need(c.get('version')==VERSION and c.get('original_window_started_at_utc')==ORIGINAL_START and
        c.get('original_deadline_utc')==(base._utc(ORIGINAL_START)+timedelta(seconds=base.WINDOW_SECONDS)).isoformat(),
        'Original continuation clock cannot reset')
    _need(set(c['bindings'])==BINDINGS|{'original_plan','new_plan'} and
        c['bindings']['original_journal']['sha256']==ORIGINAL_JOURNAL_SHA256,'Exact continuation evidence bindings required')
    allowed=c['allowed_roster'];prior=c['prior_actual_cell_ids'];counts=c['prior_actual_stage_counts']
    _need(digest(canonical(allowed))==c['allowed_roster_sha256'] and len(prior)==len(set(prior)) and not set(prior)&set(allowed),
        'Continuation roster overlaps original actual cells or changed')
    _need(set(counts)==set(STAGE_CAPS) and sum(counts.values())==len(prior) and counts['preflight']==10,'Original call consumption changed')
    _need(all(type(n) is int and 0<=n<=STAGE_CAPS[s] for s,n in counts.items()),'Invalid inherited stage consumption')
    remaining=Counter(item['stage'] for item in allowed.values())
    _need(all(remaining[s]+counts[s]==cap for s,cap in STAGE_CAPS.items()),'Combined original4510call/stage allowance changed')
    for item in allowed.values():
        _need(set(item)=={'config','stage','group_id','lane','payload_sha256'} and item['config']=='sol_subscription'
            and item['stage'] in {'main','repeat','audit'} and item['lane']==('blind_audit' if item['stage']=='audit' else 'sol_general')
            and base._sha(item['payload_sha256']),'Unapproved continuation route/stage/payload')
    _need(not policy['lanes']['second_source']['enabled'] and not policy['lanes']['isolated_agent']['enabled'],'No extra continuation lane')


def _admit(state,batch,rows):
    p=state['policy'];c=p['continuation'];lane,group,_=base._unbatch(p,batch)
    for row in rows:
        expected=c['allowed_roster'].get(row.get('cell_id'))
        _need(expected is not None and row['cell_id'] not in c['prior_actual_cell_ids'],'Original actual/unknown/failed first cannot dispatch again')
        _need((row['config'],row['split'],row['request_sha256'],lane,group)==
            (expected['config'],expected['stage'],expected['payload_sha256'],expected['lane'],expected['group_id']),
            'Request differs from exact never-dispatched frozen roster')
    counts=Counter(entry['split'] for entry in state['entries'].values())
    counts.update(row['split'] for row in rows if row['key'] not in state['entries'])
    _need(all(counts[stage]+c['prior_actual_stage_counts'][stage]<=cap for stage,cap in STAGE_CAPS.items()),
        'Original actual plus continuation reservations exceeds frozen call cap')


class ContinuationLedger(base.FollowupLedger):
    def __init__(self,path,frozen_policy=None,*,guard=None,clock=None):
        if frozen_policy is not None:
            _validate(frozen_policy)
            rebound=freeze_continuation_policy(frozen_policy['manifest_path'],prior_receipt_path=frozen_policy['prior_receipt_path'],
                prior_journal_path=frozen_policy['prior_journal_path'])
            _need(canonical(rebound)==canonical(frozen_policy),'Policy differs from exact frozen continuation proof')
            protected={Path(item['path']).resolve() for item in frozen_policy['continuation']['bindings'].values()}
            _need(Path(path).resolve() not in protected,'Never write a closed ancestor/receipt/plan')
        super().__init__(path,frozen_policy,guard=guard,clock=clock)
        with self._locked() as state:
            self._check_guard(state)
            if state['window_started_at_utc'] is None:
                self._append(state,'followup_start',{'at_utc':state['policy']['continuation']['original_window_started_at_utc']})
            else:_need(state['window_started_at_utc']==ORIGINAL_START,'Continuation clock was reset')
    @staticmethod
    def _apply(state,kind,data):
        if state is None:
            _need(kind=='initialize','Missing continuation initialization');_validate(data['policy'])
            result=base.FollowupLedger._apply(None,kind,data)
            result['last_dispatch_at_utc']=data['policy']['continuation']['original_last_dispatch_at_utc'];return result
        if kind=='followup_start':_need(data['at_utc']==ORIGINAL_START,'Continuation may start only at original first inference')
        if kind=='reserve':_admit(state,data['batch_id'],data['new_requests'])
        return base.FollowupLedger._apply(state,kind,data)
    def _check_guard(self,state):
        super()._check_guard(state)
        for item in state['policy']['continuation']['bindings'].values():self.verify_historical_file(item['path'],item['sha256'])
    def reserve_group(self,lane,group_id,requests,*,batch_id=None):
        self.verify_full_journal();rows=base._specs(requests)
        with self._locked() as state:
            self._check_guard(state);now=self._now()
            if now>=base._utc(state['window_started_at_utc'])+timedelta(seconds=base.WINDOW_SECONDS):raise base.BudgetExceeded('Original five-hour window ended')
            batch=base._batch(state['policy'],lane,group_id,batch_id or group_id)
            _admit(state,batch,rows);base._validate_specs(state,batch,rows)
            return self._reserve(state,batch,lane,rows)
