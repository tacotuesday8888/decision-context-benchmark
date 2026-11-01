import json
from pathlib import Path
import tempfile
import unittest
from scripts.study_v7.main_data import recover_external_alias, RAW
from scripts.study_v7.requests import digest


class ReconstructionTests(unittest.TestCase):
    def test_missing_alias_requires_two_locks_and_identical_source_bytes(self):
        RAW.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=RAW) as folder:
            root=Path(folder);body=b'locked synthetic input\n';sha=digest(body)
            (root/'external-selected-v3.jsonl').write_bytes(body)
            for version in (2,3):
                (root/f'external-selection-v{version}.json').write_text(json.dumps({'artifacts':{f'external-selected-v{version}.jsonl':sha}}))
            target=recover_external_alias(root,root)
            self.assertEqual(target.read_bytes(),body)
            target.unlink()
            (root/'external-selected-v3.jsonl').write_bytes(b'different input')
            with self.assertRaisesRegex(ValueError,'different source bytes'):
                recover_external_alias(root,root)
            self.assertFalse(target.exists())


if __name__=='__main__':
    unittest.main()
