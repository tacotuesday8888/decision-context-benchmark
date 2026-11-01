import copy,json,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/controls_v4'))
from continue_stream_v1 import nonterminal_timeout
class StreamContinuationTests(unittest.TestCase):
    def setUp(self):
        policy=json.loads((ROOT/'results/controls-v4/stream-continuation-v1.json').read_text())
        self.record=json.loads((ROOT/policy['record_path']).read_text())
    def test_exact_saved_empty_stream(self):
        self.assertTrue(nonterminal_timeout(self.record,'gpt-6-luna'))
        self.assertFalse(nonterminal_timeout(self.record,'gpt-6-astra'))
    def test_extra_output_error_or_usage_cannot_be_bypassed(self):
        for event in [{'type':'response.failed'},{'type':'error','code':'usage_limit_reached'},{'type':'response.output_text.delta','delta':'false'}]:
            r=copy.deepcopy(self.record);r['raw_body']+='\ndata: '+json.dumps(event)+'\n'
            self.assertFalse(nonterminal_timeout(r,'gpt-6-luna'))
        r=copy.deepcopy(self.record);r['raw_body']=r['raw_body'].replace('"usage":null','"usage":{"input_tokens":1}')
        self.assertFalse(nonterminal_timeout(r,'gpt-6-luna'))
