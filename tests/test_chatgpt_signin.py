import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import time
import unittest
from urllib.parse import urlencode

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

spec = importlib.util.spec_from_file_location(
    "signin", Path(__file__).resolve().parents[1] / "scripts/chatgpt_signin.py"
)
signin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signin)


class SigninTests(unittest.TestCase):
    def test_valid_callback(self):
        query = urlencode({"state": "expected", "code": "test-code", "client_id": "oaiapp_test"})
        self.assertEqual(signin.callback_values(query, "expected"), ("test-code", "oaiapp_test"))

    def test_invalid_callbacks(self):
        cases = [
            "state=wrong&code=x&client_id=oaiapp_test",
            "state=expected&error=access_denied",
            "state=expected&code=x&client_id=dynamic_agent_client",
            "state=expected&client_id=oaiapp_test",
            "state=expected&code=x&code=y&client_id=oaiapp_test",
        ]
        for query in cases:
            with self.subTest(query=query), self.assertRaises(ValueError):
                signin.callback_values(query, "expected")

    def test_identity_checks(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        claims = {"iss": signin.ISSUER, "aud": "oaiapp_test", "sub": "test-subject",
                  "exp": time.time() + 300, "iat": time.time(), "nonce": "test-nonce"}
        token = jwt.encode(claims, key, algorithm="RS256")
        self.assertEqual(signin.validate_identity(token, key.public_key(), "oaiapp_test", "test-nonce")["sub"], "test-subject")
        invalid = [{"iss": "https://other.example"}, {"aud": "other"},
                   {"exp": time.time() - 30}, {"nonce": "other"}]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises((ValueError, jwt.PyJWTError)):
                signin.validate_identity(jwt.encode(claims | change, key, algorithm="RS256"),
                                         key.public_key(), "oaiapp_test", "test-nonce")
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(jwt.InvalidSignatureError):
            signin.validate_identity(token, other_key.public_key(), "oaiapp_test", "test-nonce")

    def test_protected_atomic_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private" / "test.json"
            signin.private_json(target, {"test": True})
            self.assertEqual(json.loads(target.read_text()), {"test": True})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), 0o700)
            link = target.with_name("link.json")
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                signin.private_json(link, {"test": False})
            self.assertEqual(json.loads(target.read_text()), {"test": True})


if __name__ == "__main__":
    unittest.main()
