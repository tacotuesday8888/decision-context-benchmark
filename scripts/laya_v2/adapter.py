"""Pinned local typed-decision arm; immutable preparation payloads remain unchanged."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/expanded_v2'))
from adapters import state, probability
from panel import QUESTION

MODEL = 'convaiinnovations/laya-multilingual'
REVISION = '1720e3e3357cfe1e281542e223f8273b0890ca34'
SDK = '0.4.17'
MODEL_DIR = ROOT/'models/laya-multilingual-1720e3e3'
CONFIG = {'model': MODEL, 'revision': REVISION, 'sdk': 'laya=='+SDK,
          'provider': 'Convai Innovations weights / local CPU', 'kind': 'local_decision',
          'credential': None, 'context_tokens': 8192, 'head_max_len': 256,
          'device': 'cpu', 'threads': 2, 'backend': 'eager',
          'threshold': .5, 'calibration': 'publisher defaults; no fitting',
          'input_usd_per_million': 0, 'output_usd_per_million': 0, 'output_cap': None}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def request(row, condition):
    return {'model': MODEL, 'revision': REVISION, 'sdk': SDK,
            'state': state(row, condition),
            'questions': {'injection': {'type': 'noul', 'instructions': QUESTION}},
            'settings': {k: CONFIG[k] for k in ('context_tokens','head_max_len','device','threads','backend')}}


def parse(response):
    result = {'returned_model': response.get('model'), 'checkpoint': MODEL, 'revision': REVISION,
              'usage': response.get('usage', {})}
    if response.get('model') != 'laya-rl-agent':
        return dict(result, status='model_mismatch', valid=False, prediction=None)
    usage = result['usage']
    if usage.get('truncated') or usage.get('state_tokens_dropped', 0):
        return dict(result, status='truncated', valid=False, prediction=None)
    if isinstance(usage.get('input_tokens'), bool) or not isinstance(usage.get('input_tokens'), int) or usage.get('input_tokens', -1) < 1:
        return dict(result, status='missing_usage', valid=False, prediction=None)
    answer = response['answers']['injection']
    if answer.get('type') != 'noul':
        raise ValueError('Expected noul answer')
    return dict(result, **probability(answer['noul']))


def artifact_hashes():
    return {str(p.relative_to(MODEL_DIR)): digest(p.read_bytes())
            for p in sorted(MODEL_DIR.rglob('*')) if p.is_file() and '.cache' not in p.parts and p.name != 'README.md'}


class LocalDecision:
    def __init__(self):
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        os.environ['USE_TF'] = '0'
        import laya
        import torch
        if laya.__version__ != SDK:
            raise ValueError('Wrong Laya SDK version; use .venv-laya')
        manifest = json.loads((ROOT/'results/laya-v2/model-artifacts.json').read_text())
        if manifest['revision'] != REVISION or manifest['files_sha256'] != artifact_hashes():
            raise ValueError('Pinned local artifact mismatch')
        torch.set_num_threads(CONFIG['threads'])
        self.agent = laya.load(str(MODEL_DIR), device='cpu', backend='eager',
                               expected_sha256=manifest['files_sha256'])
        self.agent.model.eval()
        if str(self.agent.device) != 'cpu':
            raise ValueError('Unexpected device fallback')
        self.parameter_count = sum(p.numel() for p in self.agent.model.parameters())

    def audit(self, payload):
        # Validate exact SDK assembly before inference. A larger head must produce the
        # identical sequence: otherwise instructions/options were silently clipped.
        from laya.common import build_sequence, build_head
        internal = self.agent._to_internal(payload['questions']['injection'])
        head, _, _ = build_head(self.agent.tok, internal, CONFIG['head_max_len'])
        full_head, _, _ = build_head(self.agent.tok, internal, 4096)
        if head != full_head:
            raise ValueError('Question/options would be truncated')
        ids, markers, stats = build_sequence(self.agent.tok, payload['state'], internal,
            max_len=CONFIG['context_tokens'], head_max_len=CONFIG['head_max_len'],
            return_truncation_stats=True)
        if stats['truncated'] or stats['state_tokens_dropped'] or len(markers) != 2:
            raise ValueError('State does not fit the pinned context budget')
        return dict(stats, input_tokens=len(ids), head_tokens=len(head),
                    input_ids_sha256=digest(json.dumps(ids).encode()),
                    native_mask_strings_sanitized=payload['state'].count(self.agent.tok.mask_token))

    def predict(self, payload):
        audit = self.audit(payload)
        raw = self.agent.system_one(payload['state'], payload['questions'],
            max_len=CONFIG['context_tokens'], head_max_len=CONFIG['head_max_len'])
        parsed = parse(raw)
        if raw['usage']['input_tokens'] != audit['input_tokens']:
            raise ValueError('Actual token accounting differs from preflight')
        return raw, parsed, audit
