"""Operational formatting/hash tests only; these are not benchmark examples or labels."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/controls_v4'))
from audit_tasktracker import reconstruct
from audit_sources import sha


class ReconstructionTests(unittest.TestCase):
    def test_published_hash_is_required(self):
        record={'text_idx':0,'primary_task_index':0,'secondary_task_index':0,
                'trigger':'T','pos':0,'sep_prompt':'S','final_prompt_hash':sha('SQTA D'.replace(' ',''))}
        source=[('title','D',[{'id':'q','question':'Q'}])]
        self.assertEqual(reconstruct(record,source,['A'])[3],'T A D')
        with self.assertRaisesRegex(AssertionError,'hash mismatch'):
            reconstruct(record,source,['changed'])

    def test_end_and_middle_preserve_source_characters(self):
        source=[('title','DE',[{'id':'q','question':'Q'}])]
        for pos,candidate in [(-1,'DE T A'),(1,'D T A E')]:
            r={'text_idx':0,'primary_task_index':0,'secondary_task_index':0,'trigger':'T',
               'pos':pos,'sep_prompt':'S','final_prompt_hash':sha(''.join(('S Q '+candidate+' ').split()))}
            self.assertEqual(reconstruct(r,source,['A'])[3],candidate)


if __name__=='__main__':
    unittest.main()
