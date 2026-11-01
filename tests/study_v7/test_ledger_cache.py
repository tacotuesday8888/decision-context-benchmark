"""Synthetic accounting cache fixtures; no model, auth or network activity."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.study_v7.budget import BudgetLedger, policy, AccountingError, BudgetExceeded
from scripts.study_v7.ledger_cache import V7LedgerCacheMixin, fingerprint
from scripts.study_v6.accounting import BudgetLedger as HistoricalLedger


if issubclass(BudgetLedger, V7LedgerCacheMixin):
    class CachedLedger(BudgetLedger):
        pass
else:
    class CachedLedger(V7LedgerCacheMixin, BudgetLedger):
        def reserve_next_group(self, *args, **kwargs):
            self.verify_full_journal()
            return super().reserve_next_group(*args, **kwargs)


class UncachedLedger(BudgetLedger):
    # Preserve the legacy I/O path even after production adopts the v7 mixin.
    _read = HistoricalLedger._read
    _append = HistoricalLedger._append
    snapshot = HistoricalLedger.snapshot
    def verify_full_journal(self):
        return None # Legacy _read already validates the prefix on every read.


class PaddingLedger(CachedLedger):
    @staticmethod
    def _apply(state, kind, data):
        if kind == 'synthetic_padding':
            state['synthetic_padding_length'] = len(data['padding'])
            return state
        return BudgetLedger._apply(state, kind, data)


def frozen_policy(cap='10'):
    return policy({'openai':'0','typesafe':'0'}, {'openai':cap,'typesafe':cap},
        {'openai':cap,'typesafe':cap}, {'development':{'openai':cap,'typesafe':cap}})


def spec(key, amount='.5', provider='openai'):
    return {'key':key,'provider':provider,'reserved_usd':amount,'request_sha256':'a'*64,
            'config':'luna_responses' if provider else 'sol_subscription','split':'development'}


class JournalCache(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.path=self.root/'journal'
        self.ledger=CachedLedger(self.path,frozen_policy())
        self.ledger.reserve_batch('first','development',[spec('first')])

    def test_unchanged_reads_skip_file_body_and_preserve_snapshot_full_validation(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Unexpected full body read')):
            for _ in range(10):
                self.assertEqual(self.ledger.entry('first')['status'],'reserved')
        read_bytes = Path.read_bytes
        with patch.object(Path,'read_bytes',autospec=True,side_effect=read_bytes) as read:
            self.ledger.snapshot()
            self.assertGreaterEqual(read.call_count,1)
        with patch.object(self.ledger,'verify_full_journal',wraps=self.ledger.verify_full_journal) as full:
            self.ledger.register_schedule('development',[{'group':'g','requests':[spec('next')]}])
            self.ledger.reserve_next_group('development')
            self.assertEqual(full.call_count,1)

    def test_identical_journal_bytes_and_states_to_uncached_ledger(self):
        other_path=self.root/'ordinary'; ordinary=UncachedLedger(other_path,frozen_policy())
        ordinary.reserve_batch('first','development',[spec('first')])
        for ledger in (self.ledger,ordinary):
            ledger.mark_dispatched('first'); ledger.settle('first',None,evidence_sha256='b'*64)
            ledger.reserve_batch('second','development',[spec('second', '.2')])
            ledger.cancel_reserved('second','c'*64)
        self.assertEqual(self.path.read_bytes(),other_path.read_bytes())
        self.assertEqual(self.ledger.snapshot(),ordinary.snapshot())
        self.assertEqual(CachedLedger(self.path).snapshot(),ordinary.snapshot())
        entry=self.ledger.entry('first')
        self.assertEqual(entry['status'],'unknown_usage')
        self.assertEqual(entry['accounted_usd'],entry['reserved_usd'])

    def test_self_append_is_tail_only_and_fsyncs_without_changing_format(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Append reread entire journal')), \
             patch('scripts.study_v7.ledger_cache.os.fsync',wraps=os.fsync) as sync:
            self.ledger.mark_dispatched('first')
            self.ledger.settle('first','.1',evidence_sha256='b'*64)
            self.assertEqual(sync.call_count,4)
        self.assertEqual(self.ledger.entry('first')['accounted_usd'],'0.1')
        self.assertEqual(CachedLedger(self.path).snapshot(),self.ledger.snapshot())

    def test_same_size_prefix_mutation_with_mtime_restored_is_caught_by_ctime(self):
        before=self.path.stat(); body=self.path.read_bytes(); mutated=body.replace(b'initialize',b'INITIALIZE',1)
        self.assertEqual(len(mutated),len(body)); self.path.write_bytes(mutated)
        os.utime(self.path,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.assertEqual(self.path.stat().st_mtime_ns,before.st_mtime_ns)
        self.assertNotEqual(self.path.stat().st_ctime_ns,before.st_ctime_ns)
        with self.assertRaises(AccountingError):self.ledger.entry('first')

    def test_force_full_snapshot_catches_mutation_even_if_cache_fingerprint_is_forged(self):
        body=self.path.read_bytes(); self.path.write_bytes(body.replace(b'initialize',b'INITIALIZE',1))
        self.ledger._v7_journal_cache['fingerprint']=fingerprint(self.path)
        with self.assertRaises(AccountingError):self.ledger.snapshot()

    def test_shrink_torn_tail_replacement_and_removed_file_fail_closed(self):
        cases=('shrink','torn','replacement','removed')
        original=self.path.read_bytes()
        for case in cases:
            with self.subTest(case=case):
                path=self.root/case; path.write_bytes(original); ledger=CachedLedger(path)
                if case=='shrink':path.write_bytes(original[:-10])
                elif case=='torn':
                    with path.open('ab') as stream:stream.write(b'{"unfinished":')
                elif case=='replacement':
                    new=self.root/'replacement-new'; new.write_bytes(original); os.replace(new,path)
                else:path.unlink()
                with self.assertRaises(AccountingError):ledger.entry('first')

    def test_external_valid_append_is_fully_checked_and_cross_instance_state_is_current(self):
        other=CachedLedger(self.path)
        other.mark_dispatched('first'); other.settle('first','.2',evidence_sha256='b'*64)
        self.assertEqual(self.ledger.entry('first')['accounted_usd'],'0.2')
        self.assertEqual(self.ledger.snapshot(),other.snapshot())
        # A valid tail with a changed retained prefix is never accepted.
        body=self.path.read_bytes(); self.path.write_bytes(body.replace(b'initialize',b'INITIALIZE',1))
        with self.assertRaises(AccountingError):self.ledger.entry('first')

    def test_concurrent_compliant_writers_cannot_overreserve(self):
        path=self.root/'shared'; first=CachedLedger(path,frozen_policy('1')); second=CachedLedger(path)
        def reserve(args):
            ledger,key=args
            try:ledger.reserve_batch(key,'development',[spec(key,'.6')]); return True
            except BudgetExceeded:return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(reserve,[(first,'a'),(second,'b')]))
        self.assertEqual(sum(results),1)
        self.assertEqual(first.snapshot()['incremental_accounted_usd']['openai'],'0.6')
        self.assertEqual(first.snapshot(),second.snapshot())

    def test_subscription_supersession_and_replay_remain_identical_with_cache(self):
        import importlib.util
        from scripts.study_v7 import budget as budget_module
        location=Path(__file__).with_name('test_execution.py')
        module_spec=importlib.util.spec_from_file_location('v7_cache_supersession_fixture',location)
        module=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.SubscriptionSupersession)
        result=unittest.TestResult()
        with patch.object(budget_module,'BudgetLedger',CachedLedger):
            suite.run(result)
        self.assertEqual(result.testsRun,2)
        self.assertEqual(result.failures,[])
        self.assertEqual(result.errors,[])

    def test_failed_apply_or_partial_write_invalidates_mutated_cache_and_reopen_fails_closed(self):
        class ExplodingLedger(CachedLedger):
            @staticmethod
            def _apply(state,kind,data):
                if kind=='synthetic_apply_failure':
                    state['entries']['first']['accounted_usd']='999'
                    raise AccountingError('synthetic failed state application')
                return BudgetLedger._apply(state,kind,data)
        path=self.root/'failed-apply'; path.write_bytes(self.path.read_bytes()); ledger=ExplodingLedger(path)
        with self.assertRaisesRegex(AccountingError,'synthetic failed'):
            with ledger._locked() as state:ledger._append(state,'synthetic_apply_failure',{})
        self.assertIsNone(ledger._v7_journal_cache)
        with self.assertRaisesRegex(AccountingError,'invalidated'):ledger.entry('first')
        with self.assertRaises(AccountingError):ExplodingLedger(path)
        path=self.root/'external-apply'; path.write_bytes(self.path.read_bytes()); reader=ExplodingLedger(path)
        current=reader.snapshot()
        event={'index':current['events'],'previous_sha256':current['head_sha256'],
               'kind':'synthetic_apply_failure','data':{}}
        from scripts.study_v6.accounting import canonical,digest
        event['sha256']=digest(canonical(event))
        with path.open('ab') as stream:stream.write(canonical(event)+b'\n')
        with self.assertRaises(AccountingError):reader.entry('first')
        self.assertIsNone(reader._v7_journal_cache)
        with self.assertRaisesRegex(AccountingError,'invalidated'):reader.entry('first')
        path=self.root/'partial-write'; path.write_bytes(self.path.read_bytes()); ledger=CachedLedger(path)
        write=os.write
        def partial(fd,body):return write(fd,body[:len(body)//2])
        with patch('scripts.study_v7.ledger_cache.os.write',side_effect=partial):
            with self.assertRaisesRegex(AccountingError,'Partial journal write'):ledger.mark_dispatched('first')
        self.assertIsNone(ledger._v7_journal_cache)
        with self.assertRaises(AccountingError):CachedLedger(path)

    def test_historical_first_or_changed_hash_is_verified_and_unchanged_stat_is_cached(self):
        path=self.root/'history'; path.write_bytes(b'fixed historical costs')
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        self.ledger.verify_historical_file(path,sha)
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Unexpected fixed-history reread')):
            self.ledger.verify_historical_file(path,sha)
        before=path.stat(); path.write_bytes(b'FIXED historical costs'); os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaises(AccountingError):self.ledger.verify_historical_file(path,sha)


def benchmark(megabytes=90):
    """Temporary synthetic journal only; called explicitly, never by unittest."""
    with tempfile.TemporaryDirectory(prefix='dcb-ledger-cache-synthetic-') as temp:
        path=Path(temp)/'journal'; ledger=PaddingLedger(path,frozen_policy('100'))
        with ledger._locked() as state:
            ledger._append(state,'synthetic_padding',{'padding':'x'*(megabytes*1024*1024)})
        ledger.reserve_batch('first','development',[spec('first')])
        start=time.perf_counter()
        for _ in range(1000):ledger.entry('first')
        fast=(time.perf_counter()-start)/1000
        start=time.perf_counter(); ledger.verify_full_journal(); full=time.perf_counter()-start
        start=time.perf_counter()
        for i in range(30):
            key='small-'+str(i); ledger.reserve_batch(key,'development',[spec(key,'.01')])
            ledger.mark_dispatched(key); ledger.settle(key,'.001',evidence_sha256='b'*64)
        append=(time.perf_counter()-start)/90
        start=time.perf_counter(); reopened=PaddingLedger(path); restart=time.perf_counter()-start
        assert reopened.snapshot()['incremental_accounted_usd']==ledger.snapshot()['incremental_accounted_usd']
        return {'synthetic_journal_bytes':path.stat().st_size,'unchanged_entry_seconds':fast,
            'full_prefix_validation_seconds':full,'small_event_append_fsync_tail_verify_seconds':append,
            'restart_full_replay_seconds':restart,'actual_inference_or_invoice_records':0,
            'assumptions':'Local temporary filesystem; one 90MiB synthetic padding event; real future event count/history/provider waits differ.'}


if __name__=='__main__':unittest.main()
