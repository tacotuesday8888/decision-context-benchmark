"""Synthetic extension assembly only: no credential, source response or network."""
from collections import Counter
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.subscription_followup import prepare_extensions as e, pilot
from scripts.subscription_followup.data_capacity import counterbalanced_schedule


def fixture(n=2):
    rows = [{"id": f"synthetic:{g}:{label}", "group_id": f"fixture-group:{g}", "pair_id": f"fixture-pair:{g}",
             "source": "dtap_released_episodes", "partition": "confirmation", "task": "Read the original synthetic task.",
             "candidate": f"Complete synthetic observation {g}/{label}.\n" + "λ" * 20,
             "upstream_label": label} for g in range(n) for label in (0, 1)]
    for row in rows:
        row["candidate_sha256"] = e.digest(row["candidate"].encode())
    source_rows = b"".join(e.canonical(row) + b"\n" for row in rows)
    schedule = counterbalanced_schedule(rows, "subscription-followup-fixed-source-fixture")
    selection = {"selected_groups": n, "selected_rows": 2*n, "candidate_corpus_sha256": schedule["source_rows_sha256"],
                 "selection_manifest_sha256": "a"*64, "selected_jsonl_sha256": e.digest(source_rows), "selection_manifest": []}
    capacity = {"source_groups": n, "selection_manifest_sha256": "a"*64, "selected_jsonl_sha256": e.digest(source_rows),
                "complete_original_candidates_preserved": True, "truncation": False, "refill": False,
                "capacity": {"jev_firstparty": {"default_context_tokens": 32000}}, "summary": {},
                "schedule": {"sha256": e.digest(e.canonical(schedule)+b"\n")}, "provider_rejection_rule": "Missing; no trim/refill"}
    authored = pilot.build_plan(run_namespace=e.NAMESPACE)
    return rows, selection, capacity, schedule, authored, source_rows


class ExtensionPreparationTests(unittest.TestCase):
    def setUp(self):
        self.rows, self.selection, self.capacity, self.schedule, self.pilot, self.source_rows = fixture()

    def build(self):
        return e.assemble(self.rows, self.selection, self.capacity, self.schedule, self.pilot)

    def test_full_crossing_counts_namespace_and_preserved_order(self):
        result = self.build()
        self.assertEqual(result["group_counts"], {"second_source": 2, "isolated_agent": 12})
        self.assertEqual(result["counts"], {"jev_firstparty": 40, "sol_subscription": 64})
        self.assertEqual(result["total_cells"], 104)
        self.assertEqual(result["stage_counts"], {"secondary": {"jev_firstparty": 16, "sol_subscription": 16},
                                               "gate": {"jev_firstparty": 24}, "actor": {"sol_subscription": 48}})
        expected = [c["cell_id"] for g in self.schedule["groups"] for c in g["cells"]]
        actual = [c["cell_id"] for g in result["groups"] if g["lane"] == "second_source" for c in g["cells"]]
        self.assertEqual(actual, expected)
        for group, original in zip(result["groups"], self.schedule["groups"]):
            self.assertEqual(group["source_group_id"], original["group_id"])
            self.assertEqual(group["group_id"], "secondary:"+original["group_id"])
            for name in ("condition_order", "page_order", "config_order"):
                self.assertEqual(group[name], original[name])
        cells = [c for g in result["groups"] for c in g["cells"]]
        self.assertEqual(len({c["cell_id"] for c in cells}), len(cells))
        self.assertTrue(all(c["namespace"] == e.NAMESPACE for c in cells))
        self.assertTrue(all(not ({"key", "request_key", "manifest_sha256"} & set(c)) for c in cells))
        self.assertFalse(result["experimental_inference_authorized"])

    def test_every_source_candidate_and_payload_is_exact(self):
        lookup = {r["id"]: r for r in self.rows}
        result = self.build()
        for group in result["groups"]:
            if group["lane"] != "second_source":
                continue
            for cell in group["cells"]:
                body = cell["payload"]
                state = body.get("state") or body["input"][0]["content"]
                self.assertEqual(json.loads(state)["CANDIDATE"], lookup[cell["id"]]["candidate"])
                self.assertEqual(cell["upstream_label"], lookup[cell["id"]]["upstream_label"])
                self.assertEqual(e.digest(e.canonical(body)), cell["payload_sha256"])
                self.assertNotIn("upstream_label", body)
                self.assertEqual(cell["prepared_input_namespace"], self.schedule["namespace"])

    def test_pilot_v4_payload_variants_and_dynamic_gate_policy_unchanged(self):
        before = e.canonical(self.pilot)
        result = self.build()
        originals = {c["cell_id"]: c for g in self.pilot["groups"] for c in g["cells"]}
        gated = []
        for group in result["groups"]:
            if group["lane"] != "isolated_agent":
                continue
            self.assertEqual([c["kind"] for c in group["cells"][:2]], ["gate", "gate"])
            for cell in group["cells"]:
                original = originals[cell["cell_id"]]
                self.assertEqual(e.canonical(cell["payload"]), e.canonical(original["payload"]))
                if cell.get("arm") == "Jev_gate":
                    gated.append(cell)
                    self.assertEqual(cell["payload_variants"], original["payload_variants"])
                    policy = cell["dynamic_payload_policy"]
                    self.assertEqual(policy["gate_cell_id"], original["gate_cell_id"])
                    self.assertEqual(policy["rule"], self.pilot["gate_rule"])
                    self.assertFalse(policy["variant_selected_during_preparation"])
                    self.assertTrue(policy["at_most_one_variant_dispatched"])
                    self.assertIn("preserve missing", policy["missing_gate"])
        self.assertEqual(len(gated), 24)
        self.assertEqual(e.canonical(self.pilot), before)
        gated[0]["payload_variants"]["allowed"]["payload"]["model"] = "modified-copy-only"
        self.assertEqual(e.canonical(self.pilot), before)

    def test_changed_candidate_payload_crossing_or_capacity_binding_rejected(self):
        for name in ("candidate", "payload_hash", "missing_cell", "capacity", "corpus"):
            with self.subTest(name=name):
                rows, selection, capacity, schedule, authored, _ = fixture()
                if name == "candidate": rows[0]["candidate"] += "changed"
                elif name == "payload_hash": schedule["groups"][0]["cells"][0]["payload_sha256"] = "f"*64
                elif name == "missing_cell": schedule["groups"][0]["cells"].pop()
                elif name == "capacity": capacity["selection_manifest_sha256"] = "f"*64
                else: schedule["source_rows_sha256"] = "f"*64
                with self.assertRaises(ValueError):
                    e.assemble(rows, selection, capacity, schedule, authored)

    def test_other_pilot_version_model_or_inference_flag_rejected(self):
        for name in ("version", "model", "authorized", "namespace"):
            with self.subTest(name=name):
                authored = copy.deepcopy(self.pilot)
                if name == "version": authored["version"] = "subscription-followup-isolated-agent-3"
                elif name == "model": authored["groups"][0]["cells"][0]["payload"]["model"] = "gpt-6-luna"
                elif name == "authorized": authored["experimental_inference_authorized"] = True
                else: authored["run_namespace"] = "subscription-followup-other"
                with self.assertRaises(ValueError):
                    e.assemble(self.rows, self.selection, self.capacity, self.schedule, authored)

    def test_66_group_fixture_receipt_bindings_and_immutable_preparation(self):
        rows, selection, capacity, schedule, authored, source_rows = fixture(66)
        pilot_body = e.canonical(authored)+b"\n"
        schedule_body = e.canonical(schedule)+b"\n"
        values = {"results/subscription-followup/second-source-selection-v1.json": e.canonical(selection),
                  "results/subscription-followup/second-source-capacity-v1.json": e.canonical(capacity),
                  "data/raw/subscription-followup/second-source/selected-pairs-v1.jsonl": source_rows,
                  "data/raw/subscription-followup/second-source/second-source-proposed-schedule-v1.json": schedule_body,
                  "data/raw/subscription-followup/isolated-agent-plan-v4.json": pilot_body,
                  "results/subscription-followup/isolated-agent-preparation-v4.json": e.canonical({
                      "plan": {"sha256": e.digest(pilot_body)}, "pilot_ready": True, "inference_performed": False})}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative, body in values.items():
                target = root/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            with patch.multiple(e, SOURCE_ROWS_SHA=e.digest(source_rows), SOURCE_SCHEDULE_SHA=e.digest(schedule_body),
                                SOURCE_MANIFEST_SHA=selection["selection_manifest_sha256"], PILOT_PLAN_SHA=e.digest(pilot_body)):
                receipt = e.prepare(root)
                plan_path = root/receipt["plan"]["path"]
                original = plan_path.read_bytes()
                self.assertEqual(e.digest(original), receipt["plan"]["sha256"])
                self.assertEqual(receipt["total_cells"], 1128)
                self.assertEqual(receipt["counts"], {"jev_firstparty": 552, "sol_subscription": 576})
                self.assertFalse(receipt["inference_authorized_by_preparation"])
                self.assertFalse(receipt["actual_ledger_keys_created"])
                self.assertEqual(e.prepare(root), receipt)
                with self.assertRaises(ValueError):
                    e.prepare(root, run_namespace="subscription-followup-other")
                self.assertEqual(plan_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
