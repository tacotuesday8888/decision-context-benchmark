"""Read-only reuse of frozen request/parsing code without old runner or credentials."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/expanded_v2'))
from panel import PANEL as BASE_PANEL
from adapters import request as base_request, parse, LocalDetector
from common import sha
sys.path.insert(0, str(ROOT / 'scripts/laya_v2'))
from adapter import CONFIG as LAYA_CONFIG, request as laya_request, LocalDecision
sys.path.insert(0, str(ROOT / 'scripts/nimble_v2'))
import local as nimble
sys.path.insert(0, str(ROOT / 'scripts/expanded_execution'))
from spending import totals as provider_totals, caps as provider_caps

PANEL = dict(BASE_PANEL, laya_local=LAYA_CONFIG, nimble_local=nimble.CONFIG)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def request(config, row, condition):
    if config == 'laya_local':
        return laya_request(row, condition)
    if config == 'nimble_local':
        return nimble.request(row, condition)
    return base_request(config, row, condition)


def reserve_usd(config, payload, route):
    if route in ('local', 'subscription'):
        return 0.0
    settings = PANEL[config]
    bound = len(canonical(payload).encode()) + 4096
    return (2 * bound * settings['input_usd_per_million'] +
            (settings['output_cap'] or 0) * settings['output_usd_per_million']) / 1e6
