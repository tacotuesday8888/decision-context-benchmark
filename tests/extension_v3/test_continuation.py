"""Operational policy fixtures, not benchmark examples or labels."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/extension_v3'))
spec = importlib.util.spec_from_file_location('reviewed_continuation', ROOT / 'scripts/extension_v3/continue_reviewed.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = module.ROOT, module.OUT
        module.ROOT = Path(self.temp.name)
        module.OUT = module.ROOT / 'results/extension-v3'
        self.out = module.OUT
        (self.out / 'confirmation/luna_chat').mkdir(parents=True)
        (self.out / 'continuations').mkdir()
        (self.out / 'confirmation-freeze-v1.json').write_text('{}')
        (self.out / 'prior.json').write_text('{"specific_exception":true}')
        self.prior_hash = module.sha((self.out / 'prior.json').read_bytes())
        self.write(self.out / 'runtime-amendment-v3.0.3.json', {
            'continuation_tool_sha256': module.sha(Path(module.__file__).read_bytes()),
            'confirmation_freeze_sha256': module.sha(b'{}'),
            'prior_amendments': {'prior.json': self.prior_hash}})

    def tearDown(self):
        module.ROOT, module.OUT = self.old
        self.temp.cleanup()

    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True))

    def failure(self, name='one', status='http_error', http=0):
        directory = self.out / 'confirmation/luna_chat'
        path = directory / (name + '.json')
        self.write(path, {'job': {'config': 'luna_chat'}, 'status': 'failed',
            'parsed': {'status': status}, 'observation': {'http_status': http},
            'raw_body': '', 'started_at': '2020-01-01T00:00:00+00:00', 'elapsed_seconds': 60})
        stop = directory / ('STOP-' + name + '.json')
        self.write(stop, {'record': str(path.relative_to(module.ROOT))})
        target = self.out / 'continuations' / (module.sha(stop.read_bytes()) + '.json')
        return path, stop, target

    def resolve(self):
        with contextlib.redirect_stdout(io.StringIO()):
            module.resolve('luna_chat')

    def test_transient_resolution_is_idempotent(self):
        _, _, target = self.failure()
        self.resolve()
        before = target.read_bytes()
        self.resolve()
        self.assertEqual(before, target.read_bytes())

    def test_unresolved_semantic_error_is_not_bypassed(self):
        _, _, target = self.failure(status='invalid_format', http=200)
        with self.assertRaises(PermissionError):
            self.resolve()
        self.assertFalse(target.exists())

    def test_reviewed_special_case_does_not_block_later_transient(self):
        path, stop, target = self.failure('earlier', 'interrupted_stream', 200)
        self.write(target, {'config': 'luna_chat', 'stop_sha256': module.sha(stop.read_bytes()),
            'failure_sha256': module.sha(path.read_bytes()), 'amendment_sha256': self.prior_hash,
            'not_before_epoch': 0})
        before = target.read_bytes()
        _, _, later = self.failure('later')
        self.resolve()
        self.assertEqual(before, target.read_bytes())
        self.assertTrue(later.exists())

    def test_changed_failure_invalidates_existing_receipt(self):
        path, _, _ = self.failure()
        self.resolve()
        data = json.loads(path.read_text())
        data['elapsed_seconds'] = 61
        self.write(path, data)
        with self.assertRaises(AssertionError):
            self.resolve()


if __name__ == '__main__':
    unittest.main()
