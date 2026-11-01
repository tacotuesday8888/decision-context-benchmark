from decimal import Decimal
import copy
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from scripts.study_v6.accounting import (
    AccountingError, AlreadyDispatched, BudgetExceeded, BudgetLedger,
    money, reconcile_history, verify_history, canonical, digest, NIMBLE_LEGACY_CAPACITY_SHA256,
)


def request(key, provider, value, **extra):
    return dict(key=key, provider=provider, reserved_usd=value,
                request_sha256=hashlib.sha256(key.encode()).hexdigest(), **extra)


def group(name, openai, typesafe=None):
    return dict(group=name, requests=[request(name + ":o", "openai", openai),
                request(name + ":t", "typesafe", openai if typesafe is None else typesafe)])


def receipt(openai="0.4838404", typesafe="0.25877485200000006"):
    return dict(prior_accounted_usd=dict(openai=openai, typesafe=typesafe),
                provider_caps_usd=dict(openai="15", typesafe="20"),
                evidence_sha256={})


def contender(path, index, queue):
    try:
        ledger = BudgetLedger(path)
        ledger.reserve_batch("worker:" + str(index), "development",
                             [request("worker:" + str(index), "openai", ".1")])
        queue.put("reserved")
    except BudgetExceeded:
        queue.put("denied")


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "budget.jsonl"

    def ledger(self, **kwargs):
        return BudgetLedger(self.path, receipt(), **kwargs)

    def finish(self, ledger, keys, actual):
        for key in keys:
            ledger.mark_dispatched(key)
            ledger.settle(key, actual, evidence_sha256="b" * 64)

    def test_inherited_spend_once_and_immutable_policy(self):
        ledger = self.ledger()
        before = ledger.snapshot()
        self.assertEqual(before["all_in_accounted_usd"]["openai"], "0.4838404")
        BudgetLedger(self.path, receipt())
        self.assertEqual(before, BudgetLedger(self.path).snapshot())
        with self.assertRaises(AccountingError):
            BudgetLedger(self.path, receipt(openai="0.4838405"))
        with self.assertRaises(AccountingError):
            BudgetLedger(self.path, receipt(), caps=dict(openai="16", typesafe="20"))

    def test_decimal_exact_boundary_no_float_slack(self):
        ledger = BudgetLedger(self.path, receipt(openai="14.5"))
        ledger.reserve_batch("a", "development", [request("a", "openai", ".5")])
        self.assertEqual(ledger.snapshot()["all_in_accounted_usd"]["openai"], "15")
        with self.assertRaises(BudgetExceeded):
            ledger.reserve_batch("b", "recovery", [request("b", "openai", "0.000000000000000001")])

    def test_whole_group_both_providers_atomically_or_none(self):
        ledger = BudgetLedger(self.path, receipt(typesafe="19.95"))
        ledger.register_schedule("main", [group("g1", ".02", ".06"), group("cheap", ".01")])
        stopped = ledger.reserve_next_group("main")
        self.assertEqual(stopped["status"], "stopped")
        self.assertEqual(stopped["group"], "g1")
        self.assertEqual(stopped["unrun_groups"], 2)
        self.assertEqual(ledger.snapshot()["entries"], {})
        self.assertEqual(ledger.reserve_next_group("main"), stopped)

    def test_actual_settlement_releases_holds_beyond_upfront_prefix(self):
        # Full up-front holds allow one group (5+5 > 9), but actuals permit both.
        ledger = self.ledger()
        ledger.register_schedule("main", [group("g1", "5"), group("g2", "5")])
        first = ledger.reserve_next_group("main")
        self.assertEqual(first["status"], "admitted")
        with self.assertRaises(AccountingError):
            ledger.reserve_next_group("main")
        self.finish(ledger, first["request_keys"], ".1")
        second = ledger.reserve_next_group("main")
        self.assertEqual(second["group"], "g2")
        self.finish(ledger, second["request_keys"], ".2")
        self.assertEqual(ledger.reserve_next_group("main")["status"], "complete")
        self.assertEqual(ledger.snapshot()["allocation_accounted_usd"]["main"]["openai"], "0.3")

    def test_unknown_timeout_holds_block_and_stop_without_skip(self):
        ledger = self.ledger()
        ledger.register_schedule("main", [group("g1", "5"), group("g2", "5"), group("cheap", ".1")])
        first = ledger.reserve_next_group("main")
        self.finish(ledger, first["request_keys"], None)
        second = ledger.reserve_next_group("main")
        self.assertEqual(second["status"], "stopped")
        self.assertEqual(second["group"], "g2")
        snap = ledger.snapshot()
        self.assertTrue(snap["terminal"])
        self.assertEqual(snap["allocation_accounted_usd"]["main"]["openai"], "5")
        self.assertTrue(all(e["status"] == "unknown_usage" for e in snap["entries"].values()))

    def test_crash_after_dispatch_never_resends_or_releases_hold(self):
        ledger = self.ledger()
        ledger.reserve_batch("b", "development", [request("a", "openai", ".2")])
        ledger.mark_dispatched("a")
        reopened = BudgetLedger(self.path)
        self.assertFalse(reopened.snapshot()["terminal"])
        with self.assertRaises(AlreadyDispatched):
            reopened.mark_dispatched("a")
        self.assertEqual(reopened.snapshot()["incremental_accounted_usd"]["openai"], "0.2")
        reopened.settle("a", None, evidence_sha256="a" * 64)
        self.assertTrue(reopened.snapshot()["terminal"])

    def test_positive_unsent_cancellation_closes_without_permitting_dispatch(self):
        ledger = self.ledger()
        ledger.reserve_batch("b", "development", [request("unsent", "openai", ".1")])
        ledger.cancel_reserved("unsent", "a" * 64)
        snap = ledger.snapshot()
        entry = snap["entries"]["unsent"]
        self.assertEqual(entry["status"], "cancelled_unsent")
        self.assertEqual(entry["actual_usd"], "0")
        self.assertEqual(entry["accounted_usd"], "0")
        self.assertIn("positively_not_dispatched", entry["cancellation_reason"])
        self.assertTrue(snap["terminal"])
        before = self.path.read_bytes()
        ledger.cancel_reserved("unsent", "a" * 64)
        self.assertEqual(before, self.path.read_bytes())
        with self.assertRaises(AccountingError):
            ledger.cancel_reserved("unsent", "b" * 64)
        with self.assertRaises(AlreadyDispatched):
            ledger.mark_dispatched("unsent")
        with self.assertRaises(AccountingError):
            ledger.settle("unsent", "0")
        self.assertEqual(BudgetLedger(self.path).snapshot()["entries"]["unsent"], entry)

    def test_dispatched_or_unknown_usage_can_never_be_cancelled(self):
        ledger = self.ledger()
        ledger.reserve_batch("b", "development", [request("a", "openai", ".1")])
        ledger.mark_dispatched("a")
        with self.assertRaises(AccountingError):
            ledger.cancel_reserved("a", "a" * 64)
        ledger.settle("a", None)
        with self.assertRaises(AccountingError):
            ledger.cancel_reserved("a", "a" * 64)
        self.assertEqual(ledger.snapshot()["entries"]["a"]["accounted_usd"], "0.1")

    def test_cancelled_group_cannot_release_holds_to_advance_failed_cohort(self):
        ledger = self.ledger()
        ledger.register_schedule("main", [group("first", "5"), group("next", "5")])
        first = ledger.reserve_next_group("main")
        for key in first["request_keys"]:
            ledger.cancel_reserved(key, "a" * 64)
        self.assertTrue(ledger.snapshot()["terminal"])
        with self.assertRaises(AccountingError):
            ledger.reserve_next_group("main")
        self.assertEqual(ledger.snapshot()["schedules"]["main"]["admitted"], 1)

    def test_crash_before_dispatch_can_resume_reserved_exact_attempt(self):
        ledger = self.ledger()
        req = request("a", "openai", ".2")
        ledger.reserve_batch("b", "development", [req])
        reopened = BudgetLedger(self.path)
        count = reopened.snapshot()["events"]
        reopened.reserve_batch("b", "development", [dict(req, reserved_usd="0.20")])
        self.assertEqual(reopened.snapshot()["events"], count)
        reopened.mark_dispatched("a")
        reopened.settle("a", ".01")
        self.assertEqual(reopened.snapshot()["incremental_accounted_usd"]["openai"], "0.01")

    def test_exact_payload_refs_charged_once_within_configuration_split(self):
        ledger = self.ledger()
        shared_o, shared_t = request("confirmation:o:payload", "openai", ".1"), request("confirmation:t:payload", "typesafe", ".1")
        ledger.register_schedule("main", [dict(group="g1", requests=[shared_o, shared_t]),
                                          dict(group="g2", requests=[shared_o, shared_t])])
        first = ledger.reserve_next_group("main")
        self.finish(ledger, first["request_keys"], ".02")
        ledger.reserve_next_group("main")
        self.assertEqual(len(ledger.snapshot()["entries"]), 2)
        self.assertEqual(ledger.snapshot()["incremental_accounted_usd"]["openai"], "0.02")
        # A separate development payload/key is never a confirmation cache hit.
        ledger.reserve_batch("dev", "development", [request("development:o:payload", "openai", ".1")])
        self.assertEqual(len(ledger.snapshot()["entries"]), 3)
        with self.assertRaises(AccountingError):
            ledger.reserve_batch("bad", "development", [shared_o])

    def test_changed_payload_or_schedule_or_settlement_rejected(self):
        ledger = self.ledger()
        req = request("a", "openai", ".1")
        ledger.reserve_batch("b", "development", [req])
        with self.assertRaises(AccountingError):
            ledger.reserve_batch("b", "development", [dict(req, request_sha256="c" * 64)])
        ledger.register_schedule("main", [group("g", ".1")])
        with self.assertRaises(AccountingError):
            ledger.register_schedule("main", [group("other", ".1")])
        ledger.mark_dispatched("a")
        ledger.settle("a", ".01", evidence_sha256="a" * 64)
        prior = self.path.read_bytes()
        ledger.settle("a", ".0100", evidence_sha256="a" * 64)
        self.assertEqual(prior, self.path.read_bytes())
        with self.assertRaises(AccountingError):
            ledger.settle("a", ".02", evidence_sha256="a" * 64)

    def test_usage_over_bound_stops_and_preserves_reservation(self):
        ledger = self.ledger()
        ledger.reserve_batch("b", "development", [request("a", "openai", ".1")])
        ledger.mark_dispatched("a")
        before = self.path.read_bytes()
        with self.assertRaises(AccountingError):
            ledger.settle("a", ".100000000000000001")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(ledger.snapshot()["entries"]["a"]["accounted_usd"], "0.1")

    def test_journal_truncation_or_mutation_fails_closed(self):
        ledger = self.ledger()
        ledger.reserve_batch("b", "development", [request("a", "openai", ".1")])
        body = self.path.read_bytes()
        self.path.write_bytes(body[:-1])
        with self.assertRaises(AccountingError):
            BudgetLedger(self.path)
        self.path.write_bytes(body.replace(b'"0.1"', b'"0.2"', 1))
        with self.assertRaises(AccountingError):
            BudgetLedger(self.path)

    def test_simultaneous_contenders_cannot_oversubscribe(self):
        self.ledger()
        context = multiprocessing.get_context("fork")
        queue = context.Queue()
        processes = [context.Process(target=contender, args=(self.path, i, queue)) for i in range(9)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=10)
            self.assertEqual(process.exitcode, 0)
        results = [queue.get(timeout=2) for _ in processes]
        self.assertEqual(results.count("reserved"), 5)
        self.assertEqual(results.count("denied"), 4)
        self.assertEqual(BudgetLedger(self.path).snapshot()["incremental_accounted_usd"]["openai"], "0.5")

    def test_guard_prevents_reserve_and_dispatch_without_mutation(self):
        state = {"allowed": True}
        def guard():
            if not state["allowed"]:
                raise PermissionError("Evidence gate changed")
        ledger = self.ledger(guard=guard)
        ledger.reserve_batch("b", "development", [request("a", "openai", ".1")])
        body = self.path.read_bytes()
        state["allowed"] = False
        with self.assertRaises(PermissionError):
            ledger.mark_dispatched("a")
        self.assertEqual(self.path.read_bytes(), body)

    def test_reject_invalid_money_and_unpaired_group_schedule(self):
        ledger = self.ledger()
        for value in (float("nan"), float("inf"), "-0.1", "1e-25", True):
            with self.assertRaises(AccountingError):
                ledger.reserve_batch("bad", "development", [request("bad", "openai", value)])
        with self.assertRaises(AccountingError):
            ledger.register_schedule("main", [dict(group="g", requests=[request("o", "openai", ".1")])])
        with self.assertRaises(AccountingError):
            ledger.reserve_batch("b", "main", [request("o", "openai", ".1")])

    def test_unmetered_dispatch_cannot_bypass_paid_allocations(self):
        ledger = self.ledger()
        ledger.register_schedule("supporting", [group("paid", ".1")])
        ledger.reserve_unmetered_batch("local", [request("local", None, "0", config="laya_local")])
        ledger.mark_dispatched("local")
        ledger.settle("local", "0")
        self.assertEqual(ledger.snapshot()["incremental_accounted_usd"]["openai"], "0")
        self.assertEqual(ledger.snapshot()["schedules"]["supporting"]["admitted"], 0)
        self.assertEqual(ledger.reserve_next_group("supporting")["group"], "paid")
        with self.assertRaises(AccountingError):
            ledger.reserve_unmetered_batch("bypass", [request("api", "openai", "0")])

    def test_confirmation_payload_dedup_crosses_main_supporting_only(self):
        ledger = self.ledger()
        shared = [request("confirmation:o", "openai", ".1", config="luna_decisions", split="confirmation"),
                  request("confirmation:t", "typesafe", ".1", config="jev_firstparty", split="confirmation")]
        ledger.register_schedule("main", [dict(group="main", requests=shared)])
        ledger.register_schedule("supporting", [dict(group="support", requests=shared)])
        main = ledger.reserve_next_group("main")
        self.finish(ledger, main["request_keys"], ".03")
        support = ledger.reserve_next_group("supporting")
        self.assertEqual(support["request_keys"], main["request_keys"])
        snap = ledger.snapshot()
        self.assertEqual(len(snap["entries"]), 2)
        self.assertEqual(snap["allocation_accounted_usd"]["supporting"]["openai"], "0")
        self.assertEqual(snap["allocation_accounted_usd"]["main"]["openai"], "0.03")
        self.assertEqual(snap["entries"][shared[0]["key"]]["allocation"], "main")
        with self.assertRaises(AccountingError):
            ledger.reserve_batch("retry-with-old-key", "recovery", shared)
        with self.assertRaises(AccountingError):
            ledger.reserve_batch("dev-with-old-key", "development", shared)

    def test_snapshot_or_return_value_cannot_change_cached_journal(self):
        ledger = self.ledger()
        batch = ledger.reserve_batch("b", "development", [request("a", "openai", ".1")])
        batch["request_keys"].clear()
        snap = ledger.snapshot()
        snap["entries"]["a"]["reserved_usd"] = "0"
        self.assertEqual(ledger.snapshot()["entries"]["a"]["reserved_usd"], "0.1")
        self.assertEqual(ledger.snapshot()["batches"]["b"]["request_keys"], ["a"])

    def test_historical_file_guard_detects_changes_and_unreconciled_ledgers(self):
        base = Path(self.temp.name)
        path = base / "results/x/old-ledger.json"
        path.parent.mkdir(parents=True)
        path.write_text('{}\n')
        historical = dict(evidence_sha256={str(path.relative_to(base)): hashlib.sha256(path.read_bytes()).hexdigest()})
        verify_history(historical, base)
        extra = base / "results/v5/new-ledger.json"
        extra.parent.mkdir()
        extra.write_text('{}\n')
        with self.assertRaises(AccountingError):
            verify_history(historical, base)
        extra.unlink()
        path.write_text('{"changed":true}\n')
        with self.assertRaises(AccountingError):
            verify_history(historical, base)

    def test_historical_chain_joins_without_counting_inherited_totals_twice(self):
        base = Path(self.temp.name)
        expanded = base / "results/expanded-execution"
        expanded.mkdir(parents=True)
        for name in ("check-ledger.json", "execution-ledger-luna_decisions.json", "execution-ledger.json",
                     "local-ledger.json", "openai-ledger-v2.3.json"):
            rows = [dict(key="dev:luna_decisions:o", accounted_usd=".1"),
                    dict(key="dev:jev_firstparty:t", accounted_usd=".2")] if name == "check-ledger.json" else []
            (expanded / name).write_text(json.dumps(dict(entries=rows)))
        prior = dict(openai=".1", typesafe=".2")
        for stage, increment, totals in (("extension-v3", (".01", ".02"), (".11", ".22")),
                                         ("controls-v4", (".03", ".04"), (".14", ".26"))):
            folder = base / "results" / stage
            folder.mkdir()
            ledger = folder / "inference-ledger-v1.json"
            ledger.write_text(json.dumps(dict(entries=[dict(key=p, provider=p, accounted_usd=v,
                reserved_usd=v, status="unknown_usage" if p == "typesafe" else "settled")
                for p, v in zip(("openai", "typesafe"), increment)])))
            (folder / "request-plan-v1.json").write_text(json.dumps(dict(prior_accounted_usd=prior)))
            closure = dict(status="terminal", pending_reservations=[], in_flight_records=[],
                           unattempted_or_missing=[], prior_accounted_usd=prior,
                           all_in_conservative_accounted_usd=dict(zip(("openai", "typesafe"), totals)),
                           provider_caps_usd=dict(openai="15", typesafe="20"),
                           unknown_usage_reservations_retained=["typesafe"],
                           ledger_sha256=hashlib.sha256(ledger.read_bytes()).hexdigest())
            (folder / "execution-closure-v1.json").write_text(json.dumps(closure))
            prior = closure["all_in_conservative_accounted_usd"]
        result = reconcile_history(base)
        self.assertEqual(result["prior_accounted_usd"], dict(openai="0.14", typesafe="0.26"))
        verify_history(result, base)
        # A second inheritance of the expanded prior breaks the chain, even when
        # the final cumulative number might still fit the provider cap.
        path = base / "results/controls-v4/execution-closure-v1.json"
        corrupt = json.loads(path.read_text())
        corrupt["prior_accounted_usd"]["openai"] = ".21"
        path.write_text(json.dumps(corrupt))
        with self.assertRaises(AccountingError):
            reconcile_history(base)


class DevelopmentCapacityAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'budget.jsonl'
        self.ledger=BudgetLedger(self.path,{'prior_accounted_usd':{'openai':'0','typesafe':'0'}})
        self.key='dev-nimble-capacity'
        self.payload_hash=digest(b'complete frozen request')
        self.record={'key':self.key,'config':'nimble_local','split':'development','attempt':0,
            'first_attempt_primary':True,'request_sha256':self.payload_hash,
            'result':{'parsed':{'status':'http_error','valid':False,'prediction':None},
                'observation':{'http_status':413,'transport_exit_code':0},
                'access_route':'local','paid_request':False,'stop_required':True,
                'raw_hashes':{'response.raw':NIMBLE_LEGACY_CAPACITY_SHA256}}}
        self.record_hash=digest(canonical(self.record)+b'\n')
        self.ledger.reserve_batch('development:first-attempts','development',[
            {'key':self.key,'provider':None,'config':'nimble_local','split':'development',
             'request_sha256':self.payload_hash,'reserved_usd':'0'},
            {'key':'remaining','provider':None,'config':'nimble_local','split':'development',
             'request_sha256':'a'*64,'reserved_usd':'0'}])
        self.ledger.mark_dispatched(self.key)
        self.ledger.settle(self.key,'0',evidence_sha256=self.record_hash)

    def args(self, record=None):
        record=self.record if record is None else record
        return {'failure_record':record,'failure_evidence_sha256':digest(canonical(record)+b'\n'),
            'stop_sha256':'b'*64,'manifest_sha256':'c'*64,'manifest_path':'data/raw/amendment.json',
            'receipt_path':'results/amendment.json','receipt_sha256':'d'*64,
            'activated_at_epoch':1060,'raw_response_sha256':NIMBLE_LEGACY_CAPACITY_SHA256}

    def test_exact_legacy_failure_adds_only_nonfinancial_immutable_event(self):
        before=self.ledger.snapshot();prefix=self.path.read_bytes()
        event=self.ledger.record_development_capacity_continuation(self.key,**self.args())
        after=self.ledger.snapshot()
        self.assertEqual(before['entries'],after['entries'])
        self.assertEqual(before['policy'],after['policy'])
        self.assertEqual(before['incremental_accounted_usd'],after['incremental_accounted_usd'])
        self.assertEqual(before['continuations'],after['continuations'])
        self.assertEqual(after['development_amendments'],{self.key:event})
        self.assertTrue(self.path.read_bytes().startswith(prefix))
        events=after['events']
        self.ledger.record_development_capacity_continuation(self.key,**dict(self.args(),activated_at_epoch=2000))
        self.assertEqual(self.ledger.snapshot()['events'],events)
        self.assertEqual(BudgetLedger(self.path).snapshot()['development_amendments'],after['development_amendments'])
        with self.assertRaises(AlreadyDispatched):self.ledger.mark_dispatched(self.key)

    def test_transient_method_still_rejects_413(self):
        args=self.args();args.pop('raw_response_sha256')
        with self.assertRaisesRegex(AccountingError,'Only an invalid transient'):
            self.ledger.record_continuation(self.key,**args)
        self.assertFalse(self.ledger.snapshot()['continuations'])

    def test_valid_answer_confirmation_future_parser_or_changed_body_cannot_qualify(self):
        variants=[]
        wrong=copy.deepcopy(self.record);wrong['result']['parsed']={'status':'ok','valid':True,'prediction':0,'score':.1};variants.append(wrong)
        wrong=copy.deepcopy(self.record);wrong['split']='confirmation';variants.append(wrong)
        wrong=copy.deepcopy(self.record);wrong['result']['parser_version']='v6-routes-2';variants.append(wrong)
        wrong=copy.deepcopy(self.record);wrong['result']['observation']['transport_exit_code']=1;variants.append(wrong)
        wrong=copy.deepcopy(self.record);wrong['result']['raw_hashes']['response.raw']='e'*64;variants.append(wrong)
        for record in variants:
            with self.subTest(record=record):
                with self.assertRaises(AccountingError):
                    self.ledger.record_development_capacity_continuation(self.key,**self.args(record))
        self.assertFalse(self.ledger.snapshot()['development_amendments'])

    def test_changed_manifest_cannot_reauthorize_old_key(self):
        self.ledger.record_development_capacity_continuation(self.key,**self.args())
        with self.assertRaises(AccountingError):
            self.ledger.record_development_capacity_continuation(self.key,**dict(self.args(),manifest_sha256='e'*64))


if __name__ == "__main__":
    unittest.main()
