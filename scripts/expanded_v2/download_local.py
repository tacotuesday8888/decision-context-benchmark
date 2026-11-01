"""Download only the selected nongated publisher weights/tokenizer; no inference or payment."""
from huggingface_hub import hf_hub_download
from panel import PANEL

if __name__=='__main__':
    p=PANEL['protectai_local']
    for name in ['config.json','tokenizer_config.json','spm.model','tokenizer.json','model.safetensors']:
        hf_hub_download(p['model'],name,revision=p['revision'])
        print(name+' available')
