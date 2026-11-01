import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/expanded_execution'))
from stop_resolution import resolved,digest

class ResumeTests(unittest.TestCase):
    def test_exact_failure_delay_route_and_status_required(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);now=datetime.now(timezone.utc);r=d/'cell-0.json'
            row={'access_route':'subscription','parsed':{'valid':False},'observation':{'http_status':504,'response_headers':{'retry-after':'120'}},'started_at':now.isoformat(),'elapsed_seconds':3}
            r.write_text(json.dumps(row));stop=d/'STOP.json';stop.write_text(json.dumps({'reason':'Long Retry-After; manual resume required','retry_after':120}))
            resolution={'action':'retain_long_retry_after_cell_invalid_and_continue','stop_sha256':digest(stop),'record_file':r.name,'record_sha256':digest(r)}
            p=d/'stop-resolution.json';p.write_text(json.dumps(resolution))
            self.assertFalse(resolved(d,'subscription',now+timedelta(seconds=122)))
            self.assertTrue(resolved(d,'subscription',now+timedelta(seconds=124)))
            self.assertFalse(resolved(d,'api_key',now+timedelta(seconds=124)))
            row['observation']['http_status']=429;r.write_text(json.dumps(row));resolution['record_sha256']=digest(r);p.write_text(json.dumps(resolution))
            self.assertFalse(resolved(d,'subscription',now+timedelta(seconds=124)))
    def test_old_empty_resolution_cannot_clear_new_gateway_stop(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);p=d/'STOP.json';p.write_text(json.dumps({'reason':'Long Retry-After; manual resume required','retry_after':120}))
            (d/'stop-resolution.json').write_text(json.dumps({'stop_sha256':digest(p),'action':'retain_empty_cell_invalid_and_continue'}))
            self.assertFalse(resolved(d,'subscription'))

    def test_overload_resolution_is_exact_and_has_cooldown(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);now=datetime.now(timezone.utc);r=d/'overload-0.json'
            row={'config':'astra_chat','id':'example','access_route':'subscription','parsed':{'status':'provider_failed','valid':False,'provider_error_code':'server_is_overloaded'},'observation':{'http_status':200},'started_at':now.isoformat(),'elapsed_seconds':2}
            r.write_text(json.dumps(row));stop=d/'STOP.json';stop.write_text(json.dumps({'id':'example','status':'provider_failed','http_status':200}))
            resolution={'action':'retain_overload_cell_invalid_and_continue','stop_sha256':digest(stop),'record_file':r.name,'record_sha256':digest(r)}
            target=d/'stop-resolution.json';target.write_text(json.dumps(resolution))
            self.assertFalse(resolved(d,'subscription',now+timedelta(seconds=121)))
            self.assertTrue(resolved(d,'subscription',now+timedelta(seconds=123)))
            self.assertFalse(resolved(d,'api_key',now+timedelta(seconds=123)))
            for code in ('insufficient_quota','rate_limit_exceeded','authentication_error'):
                row['parsed']['provider_error_code']=code;r.write_text(json.dumps(row));resolution['record_sha256']=digest(r);target.write_text(json.dumps(resolution))
                self.assertFalse(resolved(d,'subscription',now+timedelta(seconds=123)))
