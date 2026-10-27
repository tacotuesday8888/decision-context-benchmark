import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

spec = importlib.util.spec_from_file_location(
    "smoke", Path(__file__).resolve().parents[1] / "scripts/smoke_access.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def events(*items):
    return "".join("data: " + json.dumps(item) + "\n\n" for item in items)


class StreamTests(unittest.TestCase):
    def test_collect_text_when_completed_envelope_has_empty_output(self):
        body = events({"type": "response.output_text.delta", "delta": "Y"},
                      {"type": "response.output_text.delta", "delta": "ES"},
                      {"type": "response.completed", "response": {"status": "completed", "output": []}})
        self.assertEqual(smoke.parse_openai_stream(body)["stream_output_text"], "YES")

    def test_done_text_is_not_duplicated_with_deltas(self):
        body = events({"type": "response.output_text.delta", "delta": "YES"},
                      {"type": "response.output_text.done", "text": "YES"},
                      {"type": "response.completed", "response": {"status": "completed"}})
        self.assertEqual(smoke.parse_openai_stream(body)["stream_output_text"], "YES")

    def test_partial_text_is_not_success(self):
        body = events({"type": "response.output_text.delta", "delta": "YES"})
        with self.assertRaises(ValueError):
            smoke.parse_openai_stream(body)

    def test_failed_terminal_event_is_not_success(self):
        body = events({"type": "response.output_text.delta", "delta": "YES"},
                      {"type": "response.failed", "response": {"status": "failed"}})
        with self.assertRaises(ValueError):
            smoke.parse_openai_stream(body)

    def test_jev_route_never_selects_paid_model(self):
        original = smoke.env_secret
        smoke.env_secret = lambda _name: "test-not-a-real-credential"
        try:
            endpoint, payload, _headers, _access = smoke.request_for("jev")
            self.assertEqual(payload["model"], "jev-1.13-free")
            self.assertEqual(endpoint, smoke.JEV_URL)
        finally:
            smoke.env_secret = original

    def test_trial_model_alias_is_not_counted_as_version_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".secrets").mkdir()
            (root / ".secrets/jevmodel-access.json").write_text(json.dumps({
                "free_token_balance": 100000, "payment_configured": False,
                "allowed_model": smoke.JEV_TRIAL_MODEL,
            }))
            (root / ".env.local").write_text("JEVMODEL_API_KEY=test-not-a-real-key\n")
            response = {"model": "jev-latest", "answers": {"is_odd": {"type": "noul", "noul": 0.99}}}
            with patch.object(smoke, "ROOT", root), patch.object(smoke, "post", return_value=(
                {"http_status": 200, "elapsed_seconds": 0.1}, json.dumps(response)
            )), patch("builtins.print"):
                result = smoke.run("jevmodel")
            self.assertEqual(result["answer"], "YES")
            self.assertFalse(result["version_confirmed"])
            self.assertFalse(result["passed"])

    def test_unverified_trial_cannot_send_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".secrets").mkdir()
            (root / ".secrets/jevmodel-access.json").write_text(json.dumps({
                "free_token_balance": 0, "payment_configured": False,
            }))
            with patch.object(smoke, "ROOT", root), patch.object(smoke, "post") as post:
                with self.assertRaises(ValueError):
                    smoke.run("jevmodel")
                post.assert_not_called()

    def test_completed_tiny_trial_cannot_send_another_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".secrets").mkdir()
            (root / ".secrets/jevmodel-access.json").write_text(json.dumps({
                "free_token_balance": 99721, "payment_configured": False,
                "allowed_model": smoke.JEV_TRIAL_MODEL,
                "successful_smoke_test_completed": True,
            }))
            with patch.object(smoke, "ROOT", root), patch.object(smoke, "post") as post:
                with self.assertRaises(ValueError):
                    smoke.run("jevmodel")
                post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
