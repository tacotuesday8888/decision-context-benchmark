"""Synthetic clocks, slots and mocked executor only; no auth/model/API activity."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from scripts.study_v7 import pacing
from scripts.study_v7.requests import canonical,digest


class Clock:
    def __init__(self):self.now=0.;self.waits=[]
    def monotonic(self):return self.now
    def utcnow(self):return datetime(2026,11,1,tzinfo=timezone.utc)+timedelta(seconds=self.now)
    def wait(self,seconds,stop):self.waits.append(seconds);self.now+=seconds


def metadata(key,proxy=100,config='luna_decisions'):
    return {'key':key,'namespace':'first','config':config,'payload_sha256':'a'*64,
            'serialization_proxy_tokens':proxy,'weight':pacing.request_weight(config,proxy)}


class Pacing(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'events.jsonl';self.clock=Clock()
    def gate(self,weights,**extra):
        return pacing.PacingGate(self.path,weights,configuration_sha256='c'*64,
            monotonic=self.clock.monotonic,utcnow=self.clock.utcnow,wait=extra.get('wait',self.clock.wait))
    def test_weight_floor_factor_and_output_allowance(self):
        self.assertEqual(pacing.request_weight('luna_decisions',100),1024)
        self.assertEqual(pacing.request_weight('luna_responses',100),1280)
        self.assertEqual(pacing.request_weight('luna_decisions',12111),24222)
        self.assertEqual(pacing.request_weight('luna_responses',12111),24478)
        for value in (0,True,-1,1.5):
            with self.assertRaises(ValueError):pacing.request_weight('luna_decisions',value)
    def test_startup_always_waits_full_window_and_is_cancellable(self):
        row=metadata('a');gate=self.gate({'a':row});stop=threading.Event()
        result=gate.acquire(row,stop)
        self.assertGreaterEqual(self.clock.now,60)
        self.assertTrue(all(0<s<=.5 for s in self.clock.waits))
        self.assertGreaterEqual(result['wait_seconds'],60)
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
        self.assertEqual(len(self.path.read_text().splitlines()),1)
        cancelled=self.gate({'a':row},wait=lambda delay,event:event.set())
        self.assertIsNone(cancelled.acquire(row,threading.Event()))
        self.assertEqual(len(self.path.read_text().splitlines()),1)
    def test_shared_rolling_window_counts_atomic_concurrent_reservations(self):
        rows={str(i):metadata(str(i),200000,'luna_responses' if i%2 else 'luna_decisions') for i in range(4)}
        stop=threading.Event();gate=self.gate(rows,wait=lambda delay,event:event.set());self.clock.now=60
        with ThreadPoolExecutor(max_workers=4) as workers:
            values=list(workers.map(lambda row:gate.acquire(row,stop),rows.values()))
        self.assertEqual(sum(x is not None for x in values),3)
        self.assertLessEqual(gate.total,1500000)
        self.assertEqual(len(self.path.read_text().splitlines()),3)
    def test_next_window_and_fresh_gate_cannot_erase_previous_minute(self):
        rows={str(i):metadata(str(i),500000) for i in range(3)};rows['2']['namespace']='repeat-1';gate=self.gate(rows);stop=threading.Event()
        gate.acquire(rows['0'],stop);first=self.clock.now
        gate.acquire(rows['1'],stop);second=self.clock.now
        self.assertGreaterEqual(second-first,60)
        fresh=self.gate(rows);fresh.acquire(rows['2'],stop)
        self.assertGreaterEqual(self.clock.now-second,60)
        self.assertEqual(fresh.events,3)
    def test_cancellation_after_durable_slot_preserves_conservative_reservation(self):
        row=metadata('a');gate=self.gate({'a':row});self.clock.now=60;stop=threading.Event()
        record=gate._record
        def cancel_after_log(metadata):record(metadata);stop.set()
        with patch.object(gate,'_record',side_effect=cancel_after_log):
            self.assertIsNone(gate.acquire(row,stop))
        self.assertEqual(gate.total,1024)
        self.assertEqual(len(self.path.read_text().splitlines()),1)

    def test_bad_log_and_oversize_weights_fail_before_dispatch(self):
        row=metadata('a');weights={'a':row}
        for body in (b'{bad}\n',b'{"unfinished":',b'{}\n'):
            self.path.write_bytes(body);self.path.chmod(0o600)
            with self.assertRaises((ValueError,KeyError,TypeError)):self.gate(weights)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError,'oversized'):self.gate({'huge':metadata('huge',1000000)})
        gate=self.gate(weights);self.clock.now=60;gate.acquire(row,threading.Event())
        with self.path.open('ab') as f:f.write(b'garbage')
        with self.assertRaises(ValueError):gate.acquire(row,threading.Event())
        self.assertIsNotNone(gate.failure)
    def test_loader_binds_every_paid_key_to_manifest_audit_and_same_payload(self):
        raw=self.root/'data/raw/study-v7';raw.mkdir(parents=True)
        token=raw/'tokens.jsonl';row=metadata('a');audit={k:v for k,v in row.items() if k!='weight'}
        token.write_bytes(canonical(audit)+b'\n')
        configuration={'version':pacing.VERSION,**pacing.FIXED,'token_audit_path':str(token.relative_to(self.root)),
            'token_audit_sha256':digest(token.read_bytes()),'log_path':'data/raw/study-v7/events.jsonl'}
        plan={'requests':{'a':row}}
        gate=pacing.from_manifest({'pacing':configuration},plan,self.root)
        self.assertEqual(gate.weights['a']['weight'],1024)
        with self.assertRaises(ValueError):pacing.from_manifest({'pacing':configuration|{'proxy_multiplier':1.5}},plan,self.root)
        with self.assertRaises(ValueError):pacing.from_manifest({'pacing':configuration|{'token_audit_sha256':'f'*64}},plan,self.root)
        with self.assertRaises(ValueError):pacing.from_manifest({'pacing':configuration},
            {'requests':{'a':row|{'payload_sha256':'b'*64}}},self.root)
        with self.assertRaises(ValueError):pacing.from_manifest({'pacing':configuration},
            {'requests':{'a':row,'b':metadata('b')}},self.root)
    def test_executor_paces_before_mark_dispatched_without_holding_ledger_lock(self):
        from scripts.study_v7 import budget,run
        module_spec=importlib.util.spec_from_file_location('v7_pacing_executor_fixture',Path(__file__).with_name('test_execution.py'))
        module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
        paced=set();mark=budget.BudgetLedger.mark_dispatched
        original_locked=budget.BudgetLedger._locked; ownership=threading.local()
        @contextmanager
        def tracked_lock(ledger):
            with original_locked(ledger) as state:
                ownership.depth=getattr(ownership,'depth',0)+1
                try:yield state
                finally:ownership.depth-=1
        testcase=self
        class Gate:
            def acquire(self,request,stop):
                if request['config'] in pacing.PAID_LUNA:
                    testcase.assertEqual(getattr(ownership,'depth',0),0)
                    paced.add(request['key'])
                return {'paced':request['config'] in pacing.PAID_LUNA}
        def checked_mark(ledger,key):
            if ledger.entry(key)['config'] in pacing.PAID_LUNA:self.assertIn(key,paced)
            return mark(ledger,key)
        with patch.object(pacing,'from_manifest',return_value=Gate()),patch.object(budget.BudgetLedger,'mark_dispatched',checked_mark),patch.object(budget.BudgetLedger,'_locked',tracked_lock):
            module.Routes()._executor_fixture()
        self.assertTrue(paced)


if __name__=='__main__':unittest.main()
