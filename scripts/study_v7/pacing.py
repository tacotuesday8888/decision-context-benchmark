"""Outcome-blind pacing for the two paid Luna routes; no provider/model calls.

A frozen serialization proxy is a planning quantity, not a native tokenizer or
certified provider rate charge. Slots cover both paid routes jointly. A new gate
always waits a complete provider window before dispatch, so a process restart or
repeat-phase transition cannot erase reservations from the previous minute.
The durable metadata log is audit evidence; safety does not rely on its replay.
"""
from __future__ import annotations
from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from scripts.study_v7.requests import canonical, digest

PAID_LUNA = ('luna_decisions', 'luna_responses')
VERSION = 'study-v7-luna-pacing-1'
EVENT_VERSION = 'study-v7-luna-pacing-event-1'
FIXED = {'window_seconds': 60, 'soft_token_budget': 1500000, 'provider_token_limit': 2000000,
    'proxy_multiplier': 2, 'minimum_request_weight': 1024, 'luna_responses_output_tokens': 256,
    'startup_cooldown_seconds': 60}


def request_weight(config, proxy_tokens):
    if config not in PAID_LUNA or type(proxy_tokens) is not int or proxy_tokens < 1:
        raise ValueError('Positive frozen proxy count and a paid Luna route required')
    return max(1024, 2*proxy_tokens) + (256 if config == 'luna_responses' else 0)


def _path(root, value):
    path = (Path(root)/value).resolve()
    allowed = (Path(root)/'data/raw/study-v7').resolve()
    if allowed not in path.parents:
        raise ValueError('Pacing artifacts must remain in ignored study-v7 raw storage')
    return path


def from_manifest(manifest, plan, root):
    configuration = manifest.get('pacing')
    if configuration is None:
        return None # Historical frozen manifests keep their original behavior.
    if configuration.get('version') != VERSION or any(configuration.get(k) != v for k,v in FIXED.items()):
        raise ValueError('Pacing configuration differs from the bounded v7.0.6 policy')
    token_path = _path(root, configuration['token_audit_path'])
    body = token_path.read_bytes()
    if digest(body) != configuration['token_audit_sha256']:
        raise ValueError('Manifest-bound token audit changed')
    wanted = {k:r for k,r in plan['requests'].items() if r['config'] in PAID_LUNA}
    weights, seen = {}, set()
    for line in body.splitlines():
        row = json.loads(line)
        key = row['key']
        if key in seen:
            raise ValueError('Duplicate token-audit request key')
        seen.add(key)
        if key not in wanted:
            continue
        request = wanted[key]
        if row.get('config') != request['config'] or row.get('payload_sha256') != request['payload_sha256']:
            raise ValueError('Token count is not bound to the exact frozen paid payload')
        proxy = row['serialization_proxy_tokens']
        weight = request_weight(request['config'], proxy)
        if weight > FIXED['soft_token_budget']:
            raise ValueError('Planned pacing weight exceeds a complete soft window; preserve input and hold dispatch')
        weights[key] = {'key':key,'namespace':request['namespace'],'config':request['config'],
            'payload_sha256':request['payload_sha256'],'serialization_proxy_tokens':proxy,'weight':weight}
    if set(weights) != set(wanted):
        raise ValueError('Frozen token-audit coverage is incomplete; no paid dispatch')
    return PacingGate(_path(root, configuration['log_path']), weights,
                      configuration_sha256=digest(canonical(configuration)))


class PacingGate:
    def __init__(self, log_path, weights, *, configuration_sha256,
                 monotonic=time.monotonic, utcnow=None, wait=None):
        self.path = Path(log_path)
        self.weights = weights
        for metadata in weights.values():
            if (metadata['weight'] != request_weight(metadata['config'], metadata['serialization_proxy_tokens']) or
                    metadata['weight'] > FIXED['soft_token_budget']):
                raise ValueError('Invalid or oversized frozen pacing weight')
        self.configuration_sha256 = configuration_sha256
        self.monotonic = monotonic
        self.utcnow = utcnow or (lambda:datetime.now(timezone.utc))
        self.wait = wait
        self.lock = threading.Lock()
        self.slots = deque()
        self.total = 0
        self.startup_until = monotonic() + FIXED['startup_cooldown_seconds']
        self.failure = None
        self.events = self._verify_existing_log()

    def _verify_existing_log(self):
        if self.path.is_symlink():
            raise ValueError('Pacing log cannot be a symbolic link')
        if not self.path.exists():
            self.log_size = 0
            return 0
        if self.path.stat().st_mode & 0o777 != 0o600:
            raise ValueError('Pacing audit log must have private mode0600')
        body = self.path.read_bytes()
        if body and not body.endswith(b'\n'):
            raise ValueError('Torn pacing log; preserve evidence and hold dispatch')
        self.log_size = len(body)
        count = 0
        for line in body.splitlines():
            event = json.loads(line)
            key = event['key']; expected = self.weights.get(key)
            if (expected is None or event.get('version') != EVENT_VERSION or event.get('index') != count or
                    event.get('pacing_configuration_sha256') != self.configuration_sha256 or
                    set(event) != set(expected) | {'version','index','acquired_at_utc','pacing_configuration_sha256'} or
                    any(event.get(k) != v for k,v in expected.items())):
                raise ValueError('Pacing audit evidence differs from the frozen request/policy')
            when = datetime.fromisoformat(event['acquired_at_utc'].replace('Z','+00:00'))
            if when.tzinfo is None:
                raise ValueError('Pacing timestamp requires explicit UTC offset')
            count += 1
        return count

    def _record(self, metadata):
        event = metadata | {'version':EVENT_VERSION,'index':self.events,
            'acquired_at_utc':self.utcnow().isoformat(),
            'pacing_configuration_sha256':self.configuration_sha256}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        line = canonical(event)+b'\n'
        fd = os.open(self.path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            current = os.fstat(fd)
            if current.st_mode & 0o777 != 0o600 or current.st_size != self.log_size:
                raise ValueError('Pacing log mode or retained size changed')
            if os.write(fd,line) != len(line):
                raise ValueError('Partial pacing log write; preserve evidence')
            os.fsync(fd)
        finally:
            os.close(fd)
        directory=os.open(self.path.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
        self.log_size += len(line)
        self.events += 1

    def acquire(self, request, stop_event):
        """Reserve rate capacity before durable dispatch intent, without a ledger lock.

        A cancellation leaves the monetary reservation unsent. A conservatively
        logged slot can survive a cancellation/crash without implying an API call.
        Any provider429 remains a preserved first-attempt failure and stops dispatch.
        """
        if request['config'] not in PAID_LUNA:
            return {'paced':False}
        metadata=self.weights.get(request['key'])
        if metadata is None or any(metadata[k] != request[k] for k in ('key','namespace','config','payload_sha256')):
            raise ValueError('Paid request is outside the frozen pacing token audit')
        started=self.monotonic()
        while True:
            with self.lock:
                if self.failure is not None:
                    raise ValueError('Pacing gate failed previously; hold dispatch') from self.failure
                if stop_event.is_set():
                    return None
                now=self.monotonic()
                if now < self.startup_until:
                    delay=min(.5,self.startup_until-now)
                else:
                    while self.slots and self.slots[0][0] <= now-FIXED['window_seconds']:
                        _,weight=self.slots.popleft();self.total-=weight
                    if self.total+metadata['weight'] <= FIXED['soft_token_budget']:
                        try:self._record(metadata)
                        except BaseException as error:
                            self.failure=error
                            raise
                        # The durable pacing slot is conservative if a failure or
                        # cancellation prevents the immediately following dispatch.
                        self.slots.append((now,metadata['weight']));self.total+=metadata['weight']
                        if stop_event.is_set():
                            return None
                        return {'paced':True,'weight':metadata['weight'],
                            'wait_seconds':self.monotonic()-started,'event_index':self.events-1}
                    delay=min(.5,max(.001,self.slots[0][0]+FIXED['window_seconds']-now))
            if self.wait is None:stop_event.wait(delay)
            else:self.wait(delay,stop_event)
