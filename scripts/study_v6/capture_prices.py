"""Archive current official price evidence only; never authenticate or infer."""
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.plan import DEST, RESULTS
from scripts.study_v6.common import ROOT
from scripts.study_v6.evidence import immutable, file_receipt

SOURCES = {
    'openai-decisions': 'https://developers.openai.com/api/docs/guides/decisions',
    'openai-pricing': 'https://developers.openai.com/api/docs/pricing',
    'typesafe-models': 'https://docs.typesafe.ai/models',
}


def main():
    target = RESULTS / 'price-verification-v1.json'
    if target.exists():
        raise ValueError('Price snapshot already exists; preserve it and version a fresh check if needed')
    receipts = {}
    for name, url in SOURCES.items():
        with urlopen(Request(url, headers={'User-Agent': 'Decision-Context-Benchmark/6'}), timeout=40) as response:
            if response.status != 200 or response.url != url:
                raise ValueError('Official price source changed URL/status')
            body = response.read()
        path = DEST / 'price-evidence' / (name + '.html')
        immutable(path, body)
        receipts[name] = dict(file_receipt(path, ROOT), url=url)
    receipt = {'version': 'v6-price-check-1', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'official_evidence': receipts, 'manually_crosschecked_current_primary_text': True,
        'base_input_usd_per_million': {'openai': '.10', 'typesafe': '.042'},
        'output_usd_per_million': {'openai': '0', 'typesafe': '0'},
        'openai_cache_usd_per_million': {'read': '.01', 'write_30m': '.125', 'write_12h': '.25'},
        'reservation_input_usd_per_million': {'openai': '.25', 'typesafe': '.084'},
        'request_tiers': 'Fixed native payloads and global endpoints; no regional, fast or long-context activation.',
        'reservation_definition': '(UTF-8 serialized bytes +4096) times frozen reservation rate /1e6; planning proxy, not certified tokenizer bound.',
        'accounting_definition': 'Returned native input usage at exact TypeSafe rate or conservative OpenAI cache-write upper. Unknown usage retains full request hold. Invoice charges not independently available.',
        'default_cache_retention_not_assumed': True, 'new_model_calls': 0, 'new_inference_spend_usd': 0}
    immutable(target, receipt)
    print(json.dumps({'price_receipt': str(target.relative_to(ROOT)), 'sources': len(receipts), 'model_calls': 0}))


if __name__ == '__main__':
    main()
