"""Download only pinned Laya artifacts and reproduce the recorded SDK metadata fix."""
import json
from adapter import MODEL, REVISION, SDK, MODEL_DIR, ROOT, artifact_hashes


def main():
    import laya
    if laya.__version__!=SDK:raise ValueError('Use pinned .venv-laya runtime')
    path=ROOT/'results/laya-v2/model-artifacts.json'
    manifest=json.loads(path.read_text())
    if manifest['revision']!=REVISION:raise ValueError('Revision mismatch')
    if MODEL_DIR.exists() and artifact_hashes()==manifest['files_sha256']:
        print('Pinned local Laya artifacts already verified');return
    from huggingface_hub import snapshot_download
    snapshot_download(MODEL,revision=REVISION,token=False,local_dir=str(MODEL_DIR),
        allow_patterns=['rl_agent_config.json','model.safetensors','tokenizer/*','encoder/config.json','README.md','LICENSE*'])
    if artifact_hashes()!=manifest['source_files_sha256']:
        raise ValueError('Downloaded source artifact mismatch')
    from laya.agent import _fix_tokenizer_config
    _fix_tokenizer_config(str(MODEL_DIR))
    if artifact_hashes()!=manifest['files_sha256']:
        raise ValueError('Runtime compatibility normalization mismatch')
    print('Pinned Laya artifacts and compatibility normalization verified')

if __name__=='__main__':main()
