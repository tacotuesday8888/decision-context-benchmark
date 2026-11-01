"""Explicit post-validation OpenAI credit deferral; no auth/network/model calls.

The original plan, schedules, first attempts and unknown-charge holds remain
intact. Mixed groups retain their original atomic reservations; only positively
never-dispatched deferred paid entries are cancelled to zero using the exact
bound receipt hash. Previously validated routes are operationally deferred, not
reclassified as intrinsically unsupported.
"""
from __future__ import annotations
import json
from pathlib import Path
from scripts.study_v7.requests import PANEL, digest

CONFIGURATIONS=frozenset(('luna_decisions','luna_responses'))
VERSION='study-v7-openai-credit-deferral-1'


def _project_path(root,name):
    path=(Path(root)/name).resolve();root=Path(root).resolve()
    if root not in path.parents:raise ValueError('Deferral artifact escapes project')
    return path


def _credit_error(value):
    if isinstance(value,dict):
        if value.get('type')=='insufficient_quota' and value.get('code')=='credit_balance_exhausted':return True
        return any(_credit_error(x) for x in value.values())
    if isinstance(value,list):return any(_credit_error(x) for x in value)
    return False


def load_deferral(manifest,authorization,plan,root):
    descriptor=manifest.get('operational_deferral')
    if descriptor is None:
        if authorization.get('operational_deferral_sha256') is not None:
            raise PermissionError('Authorization deferral lacks a matching manifest receipt')
        return None
    path=_project_path(root,descriptor['path']);sha=descriptor['sha256']
    if digest(path.read_bytes())!=sha or authorization.get('operational_deferral_sha256')!=sha:
        raise PermissionError('Operational deferral is not bound by manifest and owner authorization')
    receipt=json.loads(path.read_text())
    if (receipt.get('version')!=VERSION or set(receipt.get('configurations',[]))!=CONFIGURATIONS or
            len(receipt.get('configurations',[]))!=2 or receipt.get('provider')!='openai' or
            receipt.get('access_route')!='api_key' or receipt.get('reason_code')!='credit_balance_exhausted' or
            receipt.get('plan_sha256')!=manifest['plan_sha256']):
        raise PermissionError('Deferral scope/reason/plan differs from explicit paid OpenAI credit deferral')
    if any(PANEL[c]['provider']!='openai' or PANEL[c]['route']!='api_key' for c in CONFIGURATIONS):
        raise PermissionError('Deferral cannot change another provider or access route')
    validation=manifest.get('route_validation') or {}
    if validation.get('completed') is not True or not CONFIGURATIONS<=set(validation.get('validated_configurations',[])):
        raise PermissionError('Credit deferral requires previously validated paid configurations')
    descriptor_validation=manifest.get('route_validation_receipt') or {}
    if (descriptor_validation.get('sha256')!=receipt.get('route_validation_sha256') or
            digest(_project_path(root,descriptor_validation['path']).read_bytes())!=receipt['route_validation_sha256']):
        raise PermissionError('Original route validation receipt changed')
    prior_path=_project_path(root,receipt['prior_manifest_path'])
    if (digest(prior_path.read_bytes())!=receipt.get('prior_manifest_sha256') or
            manifest.get('previous_confirmation_manifest_sha256')!=receipt.get('prior_manifest_sha256')):
        raise PermissionError('Prior immutable manifest does not match the credit receipt')
    return OperationalDeferral(path,sha,receipt,plan)


class OperationalDeferral:
    def __init__(self,path,sha,receipt,plan):
        self.path=Path(path);self.sha256=sha;self.receipt=receipt;self.plan=plan
        self.configurations=CONFIGURATIONS
    def check(self):
        if digest(self.path.read_bytes())!=self.sha256:
            raise PermissionError('Operational deferral receipt changed during execution')
    def verify_evidence(self,ledger,execution):
        """Heavy original prefix/evidence/coverage checks once at executor startup."""
        self.check();execution=Path(execution);r=self.receipt;s=ledger.snapshot()
        size=r.get('journal_prefix_size_bytes')
        if type(size) is not int or size<=0:raise PermissionError('Deferral requires an exact preserved journal prefix')
        with ledger.path.open('rb') as stream:prefix=stream.read(size)
        if len(prefix)!=size or not prefix.endswith(b'\n') or digest(prefix)!=r.get('journal_prefix_sha256'):
            raise PermissionError('Preserved pre-deferral journal prefix changed')
        initial_inflight=set()
        for line in prefix.splitlines():
            event=json.loads(line)
            if event['kind']=='dispatch':initial_inflight.add(event['data']['key'])
            elif event['kind']=='settle':initial_inflight.discard(event['data']['key'])
        if initial_inflight:
            raise PermissionError('Original credit-stop prefix had in-flight attempts; resolve before deferral')
        if any(e['status']=='dispatched' and e.get('config') in CONFIGURATIONS for e in s['entries'].values()):
            raise PermissionError('A deferred paid dispatch intent must settle or stop; never cancel/replay')
        # Later allowed Jev/local intents retain the established completed-evidence
        # recovery path. A missing completion remains unknown and is never resent.
        stop_name=r.get('stop_record_name')
        if not isinstance(stop_name,str) or Path(stop_name).name!=stop_name or not stop_name.startswith('stop'):
            raise PermissionError('Deferral must identify an immutable stop record')
        if digest((execution/stop_name).read_bytes())!=r.get('stop_sha256'):
            raise PermissionError('Credit-exhaustion stop record changed')
        native=self.plan['schedules']['main_native'];expected={k for g in native for k in g['request_keys']}
        actual={k:e for k,e in s['entries'].items() if e['allocation']=='main_native'}
        schedule=s['schedules'].get('main_native') or {}
        if (r.get('full_native_groups')!=3000 or r.get('full_native_requests')!=48000 or
                len(native)!=3000 or len(expected)!=48000 or set(actual)!=expected or
                schedule.get('admitted')!=3000 or len(schedule.get('groups',[]))!=3000 or
                [g['group'] for g in schedule.get('groups',[])]!=[g['group'] for g in native] or
                any({x['key'] for x in actual_group['requests']}!=set(planned_group['request_keys'])
                    for actual_group,planned_group in zip(schedule.get('groups',[]),native)) or
                any(e['status'] not in ('settled','unknown_usage') for e in actual.values())):
            raise PermissionError('Post-validation deferral requires all original native confirmation attempts terminal')
        failures=r.get('failure_evidence')
        if not isinstance(failures,list) or len(failures)!=2 or len({x['key'] for x in failures})!=2:
            raise PermissionError('Deferral must retain both exact credit-exhaustion first attempts')
        for failure in failures:
            key=failure['key'];request=self.plan['requests'].get(key);entry=s['entries'].get(key)
            if (request is None or entry is None or request['config'] not in CONFIGURATIONS or
                    request['namespace']!='first' or request['split']!='confirmation' or
                    entry['provider']!='openai' or entry['status'] not in ('settled','unknown_usage')):
                raise PermissionError('Invalid credit-failure attempt scope or dispatch state')
            directory=execution/'attempts'/key;completed=(directory/'completed.json').read_bytes();raw=(directory/'response.raw').read_bytes()
            if (digest(completed)!=failure['completed_sha256'] or digest(raw)!=failure['response_raw_sha256'] or
                    entry.get('evidence_sha256')!=failure['completed_sha256']):
                raise PermissionError('Credit-failure original raw/completed evidence changed')
            metadata=json.loads(completed);parsed=metadata.get('parsed') or {}
            if (metadata.get('request_sha256')!=request['payload_sha256'] or metadata.get('namespace')!='first' or
                    metadata.get('first_attempt_primary') is not True or parsed.get('valid') is not False or
                    parsed.get('prediction') is not None):
                raise PermissionError('Deferral cannot replace a valid response or another payload/namespace')
            events=[]
            for block in raw.decode().replace('\r\n','\n').split('\n\n'):
                data='\n'.join(line[5:].lstrip(' ') for line in block.splitlines() if line.startswith('data:'))
                if data and data!='[DONE]':events.append(json.loads(data))
            if not _credit_error(events):raise PermissionError('Original provider evidence does not establish credit exhaustion')
    def cancel_reserved(self,ledger,keys):
        """Cancel only positively never-sent paid entries; no unknown hold release."""
        self.check()
        for key in keys:
            request=self.plan['requests'][key]
            if request['config'] not in CONFIGURATIONS:continue
            entry=ledger.entry(key)
            if entry is None:continue # An all-deferred allocation remains unadmitted.
            if (entry['provider']!='openai' or entry.get('config')!=request['config'] or
                    entry.get('request_sha256')!=request['payload_sha256'] or
                    PANEL[entry['config']]['route']!='api_key'):
                raise PermissionError('Deferred cancellation cannot touch another provider/route')
            if entry['status']=='dispatched':
                raise PermissionError('A deferred dispatch intent must settle or stop; never cancel/replay')
            if entry['status']=='reserved':ledger.cancel_reserved(key,self.sha256)
