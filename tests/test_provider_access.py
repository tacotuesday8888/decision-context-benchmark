from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import provider_access


class RefreshTests(unittest.TestCase):
    def test_expired_session_refreshes_and_keeps_rotating_token(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.secrets').mkdir();path=root/'.secrets/chatgpt.json'
            old={'saved_at':'2020-01-01T00:00:00Z','expires_in':3600,'client_id':'oaiapp_test',
                 'access_token':'old_access','refresh_token':'old_refresh','scopes':['chatgpt.tokens.use.direct']}
            path.write_text(json.dumps(old))
            with patch.object(provider_access,'ROOT',root), patch.object(provider_access,'read_json',return_value={
                'access_token':'new_access','refresh_token':'new_refresh','expires_in':3600}) as network:
                fresh=provider_access.subscription_credentials()
                self.assertEqual(fresh['refresh_token'],'new_refresh')
                self.assertEqual(json.loads(path.read_text())['access_token'],'new_access')
                self.assertEqual(path.stat().st_mode&0o777,0o600)
                provider_access.subscription_credentials()
                self.assertEqual(network.call_count,1)
                payload=network.call_args.kwargs['body'].decode()
                self.assertIn('grant_type=refresh_token',payload)
                self.assertIn('resource=https%3A%2F%2Fapi.openai.com%2Fv1',payload)
                self.assertNotIn('scope=',payload)

    def test_lost_scope_does_not_replace_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.secrets').mkdir();path=root/'.secrets/chatgpt.json'
            old={'saved_at':'2020-01-01T00:00:00Z','expires_in':1,'client_id':'oaiapp_test',
                 'refresh_token':'old_refresh','scopes':['chatgpt.tokens.use.direct']}
            path.write_text(json.dumps(old));before=path.read_bytes()
            with patch.object(provider_access,'ROOT',root),patch.object(provider_access,'read_json',return_value={'scope':'openid','access_token':'new'}):
                with self.assertRaises(ValueError):provider_access.subscription_credentials()
            self.assertEqual(before,path.read_bytes())


if __name__=='__main__':unittest.main()
