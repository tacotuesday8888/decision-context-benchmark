"""Pinned public upstream files; download without inference, keys, or execution of source code."""
from urllib.request import urlopen
from common import ROOT,RAW,DATA,sha,dump
import json
BIPIA='a004b69ec0dd446e0afd461d98cb5e96e120a5d0'
LLMAIL='1063bdf01ec8762b812d5e06ee768a06faa5a6f7'
LLCODE='3da2399839b285e129888161fcc8cb03169d1b43'
PARQUET='9bb98025c764ea035ecf77c47b108d4191626400'
PROTECTAI='90c9989b1a342275dd0d1a95aad283c04e075671'

def urls():
    result={}
    for domain in ['email','table','code']:
        for split in ['train','test']:
            name=f'benchmark/{domain}/{split}.jsonl'
            result[name.replace('/','__')]=f'https://raw.githubusercontent.com/microsoft/BIPIA/{BIPIA}/{name}'
    for name in ['benchmark/text_attack_train.json','benchmark/text_attack_test.json','benchmark/code_attack_train.json','benchmark/code_attack_test.json','bipia/data/base.py','bipia/data/code.py','bipia/data/table.py','bipia/data/email.py','bipia/data/utils.py','LICENSE','README.md']:
        result[name.replace('/','__')]=f'https://raw.githubusercontent.com/microsoft/BIPIA/{BIPIA}/{name}'
    for i in range(3):result[f'llmail-phase1-{i:04d}.parquet']=f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{PARQUET}/default/Phase1/{i:04d}.parquet'
    for name in ['scenarios.json','emails_for_fp_tests.json','raw_submissions_phase2.jsonl']:
        result['llmail-'+name]=f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{LLMAIL}/data/{name}'
    result['llmail-README.md']=f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{LLMAIL}/README.md'
    result['llmail-retriever.py']=f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{LLCODE}/src/agent/workloads/email_retriever.py'
    result['llmail-config.yaml']=f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{LLCODE}/src/agent/config.yaml'
    result['llmail-LICENSE']=f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{LLCODE}/LICENSE'
    return result

def prepare():
    RAW.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
    sources={}
    # Reuse byte-identical existing pinned pilot downloads, without changing them.
    for name,url in urls().items():
        path=RAW/name
        older=ROOT/'data/raw'/name.removeprefix('llmail-')
        if not path.exists() and name.startswith('llmail-') and older.exists():
            # Hard links avoid duplicating the 264MB immutable Phase2 source.
            path.hardlink_to(older)
        if not path.exists():
            temp=path.with_suffix(path.suffix+'.download')
            with urlopen(url,timeout=60) as response,temp.open('wb') as stream:
                while block:=response.read(1024*1024):stream.write(block)
            temp.replace(path)
        sources[name]={'url':url,'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size}
    result={'bipia_revision':BIPIA,'llmail_revision':LLMAIL,'llmail_code_revision':LLCODE,
            'llmail_parquet_revision':PARQUET,'sources':sources}
    destination=DATA/'sources.json'
    if destination.exists() and json.loads(destination.read_text())!=result:
        raise ValueError('Pinned upstream source changed')
    dump(destination,result)
    return result

if __name__=='__main__':print(json.dumps({'pinned_sources':len(prepare()['sources'])}))
