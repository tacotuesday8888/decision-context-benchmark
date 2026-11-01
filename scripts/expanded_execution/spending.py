"""Provider-specific caps include all earlier checks, failures and pending reservations."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/'results/expanded-execution/execution-config-v2.3.json'


def provider_for_key(key):
    fields=key.split(':')
    config=fields[1] if len(fields)>1 else ''
    if config=='jev_firstparty':return 'typesafe'
    if config in ('luna_decisions','luna_chat','astra_chat'):return 'openai'
    return None


def totals(directory):
    result={'openai':0.0,'typesafe':0.0}
    for path in directory.glob('*ledger*.json'):
        for entry in json.loads(path.read_text()).get('entries',[]):
            provider=provider_for_key(entry['key'])
            if provider:result[provider]+=entry['accounted_usd']
    return result


def caps():
    return json.loads(POLICY.read_text())['provider_spending_caps_usd']
