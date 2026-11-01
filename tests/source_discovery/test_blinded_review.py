"""Check annotation blinding while preserving actual source input and mapping."""
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "scripts/source_discovery/export_blinded_review.py"
SPEC = importlib.util.spec_from_file_location("export_blinded_review", PATH)
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class BlindedReviewTests(unittest.TestCase):
    def test_annotation_metadata_absent_source_text_exact_mapping_correct(self):
        canonical = {
            "source": {"repository": "SOURCE_NAME_SENTINEL", "revision": "REVISION_SENTINEL", "row_id": "ROW_SENTINEL"},
            "setting": "system_policy_boundary",
            "upstream_annotation": {"label": "LABEL_SENTINEL", "degree": "DEGREE_SENTINEL", "attack_source": "ATTACK_SOURCE_SENTINEL"},
            "detector_payload": {"setting": "system_policy_boundary", "trusted_policy": "Policy\nexact.",
                                 "actual_user_task": None, "submitted_user_prompt": "Original prompt with identifying canary: preserve it."},
        }
        blind, mapping = EXPORT.blind_record(canonical)
        encoded = json.dumps(blind)
        for sentinel in ["SOURCE_NAME_SENTINEL", "REVISION_SENTINEL", "ROW_SENTINEL", "LABEL_SENTINEL", "DEGREE_SENTINEL", "ATTACK_SOURCE_SENTINEL"]:
            self.assertNotIn(sentinel, encoded)
        self.assertEqual(blind["review_material"]["submitted_user_prompt"], canonical["detector_payload"]["submitted_user_prompt"])
        self.assertEqual(blind["review_material"]["trusted_policy"], "Policy\nexact.")
        self.assertEqual(mapping["source"], canonical["source"])
        self.assertEqual(mapping["upstream_annotation"], canonical["upstream_annotation"])
        self.assertEqual(mapping["review_id"], blind["review_id"])
        self.assertEqual(EXPORT.blind_record(canonical)[0]["review_id"], blind["review_id"])

    def test_message_metadata_whitelist_and_reference_role_rejection(self):
        record = {"source": {"row_id": "one"}, "setting": "indirect_tool_content", "upstream_annotation": {},
                  "detector_payload": {"setting": "indirect_tool_content", "trusted_policy": "Policy", "actual_user_task": "Task",
                     "source_conversation_inputs": [{"original_index": 1, "role": "tool_result", "tool": "search", "content": "Source", "annotation": "ANNOTATION_SENTINEL"}],
                     "candidate_message_indexes": [1]},
                  "review_only_tool_catalog": [{"name": "search", "description": "Exact tool text"}]}
        blind, _ = EXPORT.blind_record(record)
        self.assertNotIn("ANNOTATION_SENTINEL", json.dumps(blind))
        self.assertEqual(blind["review_only_tool_catalog"]["tools"], record["review_only_tool_catalog"])
        self.assertIn("unresolved", blind["review_only_tool_catalog"]["trust_status"])
        record["detector_payload"]["source_conversation_inputs"][0]["role"] = "assistant"
        record["detector_payload"]["source_conversation_inputs"][0]["content"] = "REFERENCE_SENTINEL"
        with self.assertRaises(ValueError):
            EXPORT.blind_record(record)

    def test_blank_csv_and_overwrite_protection(self):
        rows = list(csv.DictReader(io.StringIO(EXPORT.blank_reviewer_csv(["review_opaque"]).decode())))
        self.assertEqual(rows[0]["review_id"], "review_opaque")
        self.assertTrue(all(value == "" for key, value in rows[0].items() if key != "review_id"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packet"
            EXPORT.preserve_write(path, b"original", raw=False)
            EXPORT.preserve_write(path, b"original", raw=False)
            with self.assertRaises(ValueError):
                EXPORT.preserve_write(path, b"changed", raw=False)
            self.assertEqual(path.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
