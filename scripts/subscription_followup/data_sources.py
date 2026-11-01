"""Public source-byte acquisition only; no credentials, model calls or repo code.

All downloaded bytes are untrusted data. Only approved public source hosts are
accepted, redirects stay within that host allowlist, and output stays ignored.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen,HTTPRedirectHandler,build_opener

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/subscription-followup/second-source"
HOSTS={"api.github.com","github.com","raw.githubusercontent.com","huggingface.co"}


def sha(body):return hashlib.sha256(body).hexdigest()


def fetch(url,path):
    """Unauthenticated GET; preserve immutable bytes and a nonsecret receipt."""
    if urlsplit(url).scheme!="https" or urlsplit(url).hostname not in HOSTS or urlsplit(url).username or urlsplit(url).password:
        raise ValueError("Only approved HTTPS public source hosts are allowed")
    path=Path(path).resolve()
    if RAW.resolve() not in path.parents:raise ValueError("Source bytes must remain in the new ignored raw directory")
    class Redirect(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if urlsplit(newurl).scheme!="https" or urlsplit(newurl).hostname not in HOSTS or urlsplit(newurl).username or urlsplit(newurl).password:
                raise ValueError("Public source redirected outside the approved hosts")
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    request=Request(url,headers={"User-Agent":"DecisionContextBenchmark-PublicSourceAudit/1","Accept":"application/vnd.github+json"})
    with build_opener(Redirect()).open(request,timeout=45) as response:
        body=response.read(100_000_001)
        if len(body)>100_000_000:raise ValueError("Public source exceeds the 100 MB per-file limit")
        receipt={"url":url,"resolved_url":response.url,"http_status":response.status,
            "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"bytes":len(body),"sha256":sha(body),
            "content_type":response.headers.get("Content-Type"),"etag":response.headers.get("ETag"),
            "authenticated":False,"repository_code_executed":False}
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=body:raise ValueError("Refuse to overwrite changed source bytes")
    if not path.exists():path.write_bytes(body)
    receipt["path"]=str(path.relative_to(ROOT))
    path.with_suffix(path.suffix+".receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return body,receipt


def github_snapshot(repository,revision=None,*,directory):
    """Pin one public revision and obtain its complete recursive file inventory."""
    directory=Path(directory)
    if revision is None:
        body,head_receipt=fetch(f"https://api.github.com/repos/{repository}/commits/HEAD",directory/"head.json")
        revision=json.loads(body)["sha"]
    else:head_receipt=None
    body,tree_receipt=fetch(f"https://api.github.com/repos/{repository}/git/trees/{revision}?recursive=1",directory/"tree.json")
    tree=json.loads(body)
    if tree.get("truncated"):raise ValueError("Truncated source inventory cannot establish missing files")
    files=[r for r in tree["tree"] if r["type"]=="blob"]
    return {"repository":repository,"revision":revision,"files":files,"tree_receipt":tree_receipt,"head_receipt":head_receipt}
