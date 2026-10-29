import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/expanded_execution'))
import audit_execution as a

class AuditTests(unittest.TestCase):
    def test_execution_verifier_not_same_named_preparation_module(self):
        self.assertEqual(Path(a.verify.__code__.co_filename).resolve(),(a.ROOT/'scripts/expanded_execution/verify.py').resolve())
    def test_native_loaded_identity_checked_independently(self):
        p=next((a.OUT/'checks/nimble_local').glob('*-0.json'))
        r=json.loads(p.read_text());a.audit_native(r)
        bad=copy.deepcopy(r);bad['observation']['loaded_models']['models'][0]['digest']='wrong'
        with self.assertRaises(AssertionError):a.audit_native(bad)
        bad=copy.deepcopy(r);bad['parsed']['usage']['input_tokens']=999999
        with self.assertRaises(AssertionError):a.audit_native(bad)
