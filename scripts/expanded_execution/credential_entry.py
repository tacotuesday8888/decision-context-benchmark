"""One-time loopback password form writing only the project's ignored .env.local."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
from urllib.parse import parse_qs

ROOT=Path(__file__).resolve().parents[2]


def write_secret(name, value):
    if name not in ('OPENAI_API_KEY','TYPESAFE_API_KEY'):
        raise ValueError('Unsupported credential')
    value=value.strip()
    prefix='sk-' if name=='OPENAI_API_KEY' else 'apikey_'
    if not value.startswith(prefix) or len(value)<24 or re.search(r'\s',value):
        raise ValueError('Invalid credential format')
    path=ROOT/'.env.local'
    if path.is_symlink():raise ValueError('Refuse symlink target')
    if subprocess.run(['git','check-ignore','-q','--','.env.local'],cwd=ROOT).returncode:
        raise ValueError('Target must be Git ignored')
    tracked=subprocess.run(['git','ls-files','--error-unmatch','.env.local'],cwd=ROOT,capture_output=True)
    if tracked.returncode==0:raise ValueError('Refuse tracked credential file')
    original=path.read_text() if path.exists() else ''
    lines=original.splitlines(keepends=True)
    matching=[i for i,l in enumerate(lines) if re.match(r'^\s*(?:export\s+)?'+name+r'\s*=',l)]
    if len(matching)>1:raise ValueError('Duplicate credential entries')
    if matching:lines[matching[0]]=name+'='+value+'\n'
    else:
        if lines and not lines[-1].endswith('\n'):lines[-1]+='\n'
        lines.append(name+'='+value+'\n')
    fd,temp=tempfile.mkstemp(prefix='.env.local.tmp-',dir=ROOT)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f:f.write(''.join(lines))
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def main():
    p=argparse.ArgumentParser();p.add_argument('name',choices=['OPENAI_API_KEY','TYPESAFE_API_KEY']);a=p.parse_args()
    nonce=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,body):
            self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body.encode())
        def do_GET(self):
            if self.path!='/'+nonce:self.respond(404,'Not found');return
            self.respond(200,f'<title>Secure project credential entry</title><h1>Decision Context Benchmark</h1>'
                f'<p>Save {html.escape(a.name)} only to this project’s ignored .env.local (owner-only permissions).</p>'
                f'<form method="post" action="/{nonce}"><label>API key <input name="credential" type="password" autocomplete="off" required></label>'
                '<button type="submit">Save securely</button></form>')
        def do_POST(self):
            origin='http://127.0.0.1:'+str(self.server.server_port)
            if self.path!='/'+nonce or self.headers.get('Origin')!=origin:
                self.respond(403,'Forbidden');return
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<16384:self.respond(400,'Invalid request');return
            value=parse_qs(self.rfile.read(size).decode()).get('credential',[''])[0]
            try:write_secret(a.name,value)
            except ValueError as e:self.respond(400,str(e));return
            self.respond(200,'<title>Credential saved</title><h1>Credential saved securely</h1><p>No secret is displayed. You may close this tab.</p>')
            self.server.saved=True
    server=HTTPServer(('127.0.0.1',0),Handler);server.timeout=1;server.saved=False
    print('http://127.0.0.1:'+str(server.server_port)+'/'+nonce,flush=True)
    import time
    deadline=time.monotonic()+1200
    while not server.saved and time.monotonic()<deadline:server.handle_request()
    server.server_close()
    print('Credential saved.' if server.saved else 'Entry expired; no secret written.',flush=True)

if __name__=='__main__':main()
