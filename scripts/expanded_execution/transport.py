"""No redirects/retries; credentials only through curl stdin, retain partial streams."""
import json
from pathlib import Path
import subprocess
import tempfile
import time


def post(url, payload, headers):
    if url not in ('https://api.typesafe.ai/v1/systemone', 'https://api.openai.com/v1/decisions',
                   'https://api.openai.com/v1/responses'):
        raise ValueError('Unapproved inference endpoint')
    with tempfile.TemporaryDirectory(prefix='decision-context-execution-') as temporary:
        root = Path(temporary)
        req, response, response_headers = (root/n for n in ('request.json','response.txt','headers.txt'))
        req.write_text(json.dumps(payload))
        config = ['url = '+json.dumps(url), 'request = "POST"',
                  'header = "Content-Type: application/json"',
                  'data-binary = '+json.dumps('@'+str(req)),
                  'output = '+json.dumps(str(response)), 'dump-header = '+json.dumps(str(response_headers)),
                  'write-out = "%{http_code}"', 'silent', 'show-error',
                  'connect-timeout = 10', 'max-time = 60']
        for name, value in headers.items():
            if any(c in value for c in '\r\n'):
                raise ValueError('Invalid header')
            config.append('header = '+json.dumps(name+': '+value))
        start = time.perf_counter()
        try:
            r = subprocess.run(['/usr/bin/curl','--config','-'], input='\n'.join(config)+'\n',
                               capture_output=True, text=True, timeout=65, check=False)
            code, status = r.returncode, int(r.stdout) if r.stdout.isdigit() else 0
        except subprocess.TimeoutExpired:
            code, status = 124, 0
        safe_headers = {}
        if response_headers.exists():
            for line in response_headers.read_text().splitlines():
                if ':' in line:
                    key, value = line.split(':',1)
                    if key.lower() in ('retry-after','x-request-id','request-id','x-tokens-remaining'):
                        safe_headers[key.lower()] = value.strip()
        return {'http_status':status, 'transport_exit_code':code,
                'elapsed_seconds':round(time.perf_counter()-start,3), 'response_headers':safe_headers}, \
               response.read_text() if response.exists() else ''
