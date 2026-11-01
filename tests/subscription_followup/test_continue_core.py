"""Offline continuation contracts: synthetic records, mocked permit/ledger/events."""
import copy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.subscription_followup import continue_core as c
from scripts.subscription_followup import run, transport


ANCHOR = "2026-11-01T12:00:00+00:00"
GROUP = {"stage": "main", "group_id": "synthetic-group"}


def overload(key="synthetic-overload"):
    return {"key": key, "config": "sol_subscription",
            "parsed": {"status": "provider_failed", "valid": False,
                       "termination": "failed", "returned_model": "gpt-6.1-sol",
                       "error_code": "server_is_overloaded", "error_type": "service_unavailable_error"},
            "observation": {"http_status": 200, "transport_exit_code": 0, "response_headers": {}}}


def valid(key="synthetic-valid"):
    return {"key": key, "config": "sol_subscription", "parsed": {"status": "ok", "valid": True},
            "observation": {"http_status": 200, "transport_exit_code": 0, "response_headers": {}}}


def changed(record, path, value):
    result = copy.deepcopy(record)
    target = result
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    return result


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.number = 0
        # Any unexpected execution path fails before credentials or HTTP.
        for owner, name in ((transport, "_credential"), (transport, "_post"), (run, "invoke")):
            patcher = patch.object(owner, name, side_effect=AssertionError("Offline test cannot invoke transport"))
            spy = patcher.start()
            self.addCleanup(patcher.stop)
            self.addCleanup(spy.assert_not_called)

    def permit(self, *, entries=None, anchor=ANCHOR):
        self.number += 1
        execution = self.root / str(self.number)
        execution.mkdir()
        ledger = Mock()
        ledger.snapshot.return_value = {"entries": {} if entries is None else copy.deepcopy(entries),
                                        "window_started_at_utc": anchor}
        ledger.remaining_seconds.return_value = 3600.
        return SimpleNamespace(execution=execution, ledger=ledger,
            manifest={"continuation": {"original_window_started_at_utc": ANCHOR}}, check=Mock())

    def runner(self):
        permit = self.permit()
        result = c.ContinuationExecutor(permit)
        result.event = Mock()
        return result

    def test_exact_structured_overload_predicate(self):
        self.assertTrue(c.structured_overload(overload()))
        mutations = [
            (("config",), "jev_firstparty"), (("config",), "sol_responses"),
            (("observation", "http_status"), 503), (("observation", "http_status"), 429),
            (("observation", "transport_exit_code"), 28),
            (("parsed", "status"), "model_mismatch"), (("parsed", "status"), "http_error"),
            (("parsed", "termination"), "completed"), (("parsed", "termination"), None),
            (("parsed", "returned_model"), "gpt-6-luna"), (("parsed", "returned_model"), "unknown"),
            (("parsed", "error_code"), "subscription_sharing_usage_limit_exceeded"),
            (("parsed", "error_code"), "credit_balance_exhausted"),
            (("parsed", "error_code"), "invalid_model"), (("parsed", "error_code"), "unknown_error"),
            (("parsed", "error_type"), "insufficient_quota"),
            (("parsed", "error_type"), "invalid_request_error"),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                self.assertFalse(c.structured_overload(changed(overload(), path, value)))
        self.assertFalse(c.structured_overload({}))

    def test_nonmatching_http200_failures_are_fatal_not_availability(self):
        mutations = [
            (("config",), "jev_firstparty"),
            (("observation", "transport_exit_code"), 28),
            (("parsed", "status"), "model_mismatch"),
            (("parsed", "termination"), "completed"),
            (("parsed", "returned_model"), "gpt-6-luna"),
            (("parsed", "error_code"), "subscription_sharing_usage_limit_exceeded"),
            (("parsed", "error_code"), "credit_balance_exhausted"),
            (("parsed", "error_code"), "invalid_parameter"),
            (("parsed", "error_code"), "unknown_error"),
            (("parsed", "error_type"), "insufficient_quota"),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                runner = self.runner()
                record = changed(overload(), path, value)
                runner.observe(GROUP, record)
                self.assertTrue(runner.fatal.is_set())
                self.assertFalse(runner.pause.is_set())
                self.assertEqual(len(runner.service_failures), 1, "Only the seeded original event is availability")
                fatal = [call.kwargs for call in runner.event.call_args_list if call.args[0] == "fatal_failure"]
                self.assertEqual(len(fatal), 1)
                self.assertEqual(fatal[0]["http_status"], 200)
                self.assertEqual(fatal[0]["error_code"], record["parsed"]["error_code"])

    def test_actual_http200_and_error_code_survive_availability_event(self):
        runner = self.runner()
        runner.observe(GROUP, overload())
        self.assertTrue(runner.pause.is_set())
        self.assertFalse(runner.fatal.is_set())
        self.assertEqual(runner.completed["provider_failed"], 1)
        self.assertEqual(runner.service_failures[0]["key"], c.OVERLOAD_KEY)
        row = runner.service_failures[-1]
        self.assertEqual(row["http_status"], 200)
        self.assertEqual(row["error_code"], "server_is_overloaded")
        service = [call.kwargs for call in runner.event.call_args_list if call.args[0] == "service_failure"]
        self.assertEqual(service, [row])

    def test_three_consecutive_overloads_stop(self):
        runner = self.runner()
        for i in range(3):
            runner.observe(GROUP, overload(f"failure-{i}"))
            self.assertEqual(runner.fatal.is_set(), i == 2)
        self.assertEqual(runner.consecutive_service_failures, 3)
        self.assertEqual(len(runner.service_failures), 4)
        self.assertEqual(runner.reason, "bounded_service_recovery_exhausted")

    def test_old_overload_counts_toward_five_total_and_valid_resets_consecutive(self):
        runner = self.runner()
        self.assertEqual(len(runner.service_failures), 1)
        for i in range(4):
            runner.observe(GROUP, overload(f"failure-{i}"))
            self.assertFalse(runner.fatal.is_set())
            runner.observe(GROUP, valid(f"valid-{i}"))
            self.assertEqual(runner.consecutive_service_failures, 0)
        self.assertEqual(len(runner.service_failures), 5)
        runner.observe(GROUP, overload("sixth-total"))
        self.assertTrue(runner.fatal.is_set())
        self.assertEqual(runner.consecutive_service_failures, 1)
        self.assertEqual(runner.reason, "bounded_service_recovery_exhausted")

    def test_long_retry_after_remains_fatal_for_http503(self):
        runner = self.runner()
        record = {"key": "synthetic-503", "config": "sol_subscription",
                  "parsed": {"status": "http_error", "valid": False},
                  "observation": {"http_status": 503, "response_headers": {"retry-after": "1200"}}}
        runner.observe(GROUP, record)
        self.assertTrue(runner.fatal.is_set())
        self.assertEqual(runner.reason, "provider_retry_interval_exceeds_bound")
        self.assertEqual(runner.service_failures[-1]["retry_after_seconds"], 1200.)

    def test_long_retry_after_remains_fatal_for_structured_http200(self):
        for header in ("1200", format_datetime(datetime.now(timezone.utc) + timedelta(seconds=1200), usegmt=True)):
            with self.subTest(header=header):
                runner = self.runner()
                record = overload()
                record["observation"]["response_headers"] = {"retry-after": header}
                runner.observe(GROUP, record)
                self.assertTrue(runner.fatal.is_set())
                self.assertEqual(runner.reason, "provider_retry_interval_exceeds_bound")
                self.assertGreater(runner.service_failures[-1]["retry_after_seconds"], 1100.)
                self.assertEqual(runner.service_failures[-1]["http_status"], 200)

    def test_restore_accepts_only_fresh_empty_ledger_with_original_anchor(self):
        permit = self.permit()
        before = copy.deepcopy(permit.ledger.snapshot.return_value)
        runner = c.ContinuationExecutor(permit)
        self.assertEqual(list(runner.attempts.iterdir()), [])
        self.assertEqual(permit.ledger.snapshot.return_value, before)
        permit.check.assert_not_called()
        for wrong in (None, "2026-11-01T13:00:00+00:00"):
            with self.subTest(anchor=wrong), self.assertRaises(PermissionError):
                c.ContinuationExecutor(self.permit(anchor=wrong))

    def test_restore_denies_any_prior_attempt_or_entry(self):
        permit = self.permit()
        directory = permit.execution / "attempts" / "synthetic-original-intent"
        directory.mkdir(parents=True)
        (directory / "started.json").write_text("{}")
        with self.assertRaises(PermissionError):
            c.ContinuationExecutor(permit)
        for status in ("reserved", "dispatched", "settled", "unknown_usage", "cancelled_unsent"):
            with self.subTest(status=status), self.assertRaises(PermissionError):
                c.ContinuationExecutor(self.permit(entries={"old-key": {"status": status}}))


if __name__ == "__main__":
    unittest.main()
