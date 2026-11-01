"""Reuse only this project's explicitly authorized credentials; never use Codex caches."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from chatgpt_signin import private_json, read_json, ISSUER, RESOURCE
from smoke_access import ROOT, env_secret


def subscription_credentials():
    path = ROOT / '.secrets/chatgpt.json'
    if path.is_symlink():
        raise ValueError('Symlink credential file')
    # Serialize refresh-token rotation between project processes.
    with (path.parent / 'refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text())
        saved = datetime.fromisoformat(data['saved_at'].replace('Z', '+00:00')).timestamp()
        if datetime.now(timezone.utc).timestamp() > saved + data.get('expires_in', 0) - 120:
            if not data.get('refresh_token'):
                raise ValueError('Returning browser sign-in required: no refresh token')
            fresh = read_json(ISSUER + '/api/accounts/oauth/token', body=urlencode({
                'grant_type': 'refresh_token', 'client_id': data['client_id'],
                'refresh_token': data['refresh_token'], 'resource': RESOURCE,
            }).encode())
            scopes = fresh.get('scope', ' '.join(data['scopes'])).split()
            if 'chatgpt.tokens.use.direct' not in scopes:
                raise ValueError('Subscription permission missing')
            for key in ['access_token', 'refresh_token', 'id_token', 'expires_in', 'token_type']:
                if key in fresh:
                    data[key] = fresh[key]
            data['scopes'] = scopes
            data['saved_at'] = datetime.now(timezone.utc).isoformat()
            private_json(path, data)
        if 'chatgpt.tokens.use.direct' not in data['scopes']:
            raise ValueError('Subscription permission missing')
        return data


def catalog(provider):
    if provider == 'openai':
        data = subscription_credentials()
        return read_json(RESOURCE + '/models', token=data['access_token'])
    if provider == 'gemini':
        request = Request('https://generativelanguage.googleapis.com/v1beta/models',
                          headers={'x-goog-api-key': env_secret('GEMINI_API_KEY')})
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    raise ValueError('Unknown provider')


if __name__ == '__main__':
    # Catalog requests authenticate but do not perform inference.
    record = {'checked_at': datetime.now(timezone.utc).isoformat(), 'inference': False}
    for provider in ['openai', 'gemini']:
        try:
            data = catalog(provider)
            names = [item.get('slug', item.get('name')) for item in data['models']]
            record[provider] = {'authenticated': True, 'models': names}
        except Exception as error:
            record[provider] = {'authenticated': False, 'error_type': type(error).__name__,
                                'http_status': getattr(error, 'code', None)}
    destination = ROOT / 'results/pilot/access.json'
    destination.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
