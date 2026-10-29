"""Bound STOP resolutions to exact saved failures, with no retry of failed cells."""
from datetime import datetime, timezone
import hashlib
import json
import math


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolved(directory, access, now=None):
    stop=directory/'STOP.json'; path=directory/'stop-resolution.json'
    if access!='subscription' or not path.exists():return False
    resolution=json.loads(path.read_text()); stopped=json.loads(stop.read_text())
    if resolution.get('stop_sha256')!=digest(stop):return False
    action=resolution.get('action')
    if action=='retain_empty_cell_invalid_and_continue':
        # Historical resolution is valid only for the original empty-stream STOP.
        if stopped.get('status')!='interrupted_stream' or stopped.get('http_status')!=200:return False
        for p in directory.glob('*-0.json'):
            r=json.loads(p.read_text())
            if r['id']==stopped.get('id') and r['observation'].get('http_status')==200 and not r['raw_body'] and not r['observation'].get('transport_exit_code'):return True
        return False
    if action!='retain_long_retry_after_cell_invalid_and_continue':return False
    if stopped.get('reason')!='Long Retry-After; manual resume required':return False
    name=resolution.get('record_file','')
    if '/' in name or '\\' in name or not name.endswith('-0.json'):return False
    record_path=directory/name
    if not record_path.exists() or resolution.get('record_sha256')!=digest(record_path):return False
    r=json.loads(record_path.read_text()); obs=r['observation']
    if r['access_route']!='subscription' or r['parsed']['valid'] or obs.get('http_status') not in (500,502,503,504):return False
    try:
        delay=float(obs.get('response_headers',{}).get('retry-after'))
        end=datetime.fromisoformat(r['started_at'])
    except (TypeError,ValueError):return False
    if not math.isfinite(delay) or delay<=60 or delay!=stopped.get('retry_after') or end.tzinfo is None:return False
    # Existing runner timestamps the record after transport returns. Adding its
    # elapsed time is deliberately conservative even for that historical convention.
    elapsed=r.get('elapsed_seconds',0)
    if not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or elapsed<0:return False
    return ((now or datetime.now(timezone.utc))-end).total_seconds()>=delay+elapsed
