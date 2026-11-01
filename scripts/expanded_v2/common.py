"""Shared v2 paths and deterministic hashes; never mutates pilot artifacts."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/expanded-v2'
DATA=ROOT/'data/expanded-v2'
OUT=ROOT/'results/expanded-v2'
VERSION='expanded-v2.0'
SEED='decision-context-expanded-v2.0'

def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()

def norm(value):return re.sub(r'\s+',' ',value.lower()).strip()
def rank(value):return sha(SEED+value)
def dump(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
def jsonl(path):return [json.loads(line) for line in path.read_text().splitlines()]
