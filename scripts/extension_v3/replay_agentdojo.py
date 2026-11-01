"""Offline clean fixture replay; no agent, LLM, credentials or real tool services."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/raw/extension-v3/agentdojo'
REVISION = '357c80dea9af34323f709c3505d9e6d224654c7e'


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def main():
    if subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() != REVISION:
        raise ValueError('Reviewed source revision changed')
    if subprocess.check_output(['git', '-C', str(SOURCE), 'diff', '--name-only'], text=True).strip():
        raise ValueError('Upstream tracked code modified')
    # No environment credentials can reach imported SDKs. Do not read local env files.
    for name in list(os.environ):
        if any(part in name.upper() for part in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')):
            del os.environ[name]
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['LANGCHAIN_TRACING_V2'] = 'false'

    def no_network(*args, **kwargs):
        raise PermissionError('Offline fixture replay forbids network access')

    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network
    socket.getaddrinfo = no_network

    from agentdojo.task_suite import get_suite
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
    import agentdojo
    if Path(agentdojo.__file__).resolve().parent != SOURCE / 'src/agentdojo':
        raise ValueError('Unexpected installed source')
    rows, failures, tasks = [], [], []
    for suite_name in ('workspace', 'travel', 'banking', 'slack'):
        suite = get_suite('v1.2', suite_name)
        for task_id, task in sorted(suite.user_tasks.items()):
            env = suite.load_and_inject_default_environment({})
            runtime = FunctionsRuntime(suite.tools)
            task_key = suite_name + ':' + task_id
            tasks.append(task_key)
            try:
                calls = task.ground_truth(env.model_copy(deep=True))
            except Exception as error:
                failures.append({'task': task_key, 'stage': 'ground_truth', 'error_type': type(error).__name__})
                continue
            for step, call in enumerate(calls):
                try:
                    result, error = runtime.run_function(env, call.function, dict(call.args))
                    if error is not None:
                        raise ValueError('Simulator returned tool error')
                    text = tool_result_to_str(result)
                except Exception as error:
                    failures.append({'task': task_key, 'step': step, 'stage': 'tool', 'error_type': type(error).__name__})
                    # A failed dependency makes downstream replay unreliable.
                    break
                rows.append({'source': 'AgentDojo', 'source_revision': REVISION,
                    'benchmark_version': 'v1.2', 'task': task_key, 'step': step,
                    'function': call.function, 'arguments': dict(call.args),
                    'candidate': text, 'trusted_task': task.PROMPT,
                    'candidate_sha256': sha(text), 'task_sha256': sha(task.PROMPT),
                    'label_evidence': 'default_environment_ground_truth_replay_no_injection',
                    'gold': None, 'eligibility': 'pending_content_and_provenance_review',
                    'formatter': 'pinned upstream tool_result_to_str (JSON default in this revision)'})
    output = ROOT / 'data/raw/extension-v3/agentdojo-clean-replay.jsonl'
    output.write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows))
    inventory = [{k: v for k, v in row.items() if k not in ('candidate', 'trusted_task', 'arguments')}
                 | {'candidate_characters': len(row['candidate'])} for row in rows]
    out = ROOT / 'results/extension-v3'
    (out / 'agentdojo-clean-inventory.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in inventory))
    receipt = {'source_revision': REVISION, 'benchmark_version': 'v1.2',
        'tasks_attempted': len(tasks), 'tool_outputs': len(rows),
        'distinct_candidates': len({r['candidate_sha256'] for r in rows}),
        'tasks_with_outputs': len({r['task'] for r in rows}),
        'failures': failures, 'model_requests': 0, 'network_permitted': False,
        'raw_output_sha256': sha(output.read_bytes()),
        'script_sha256': sha(Path(__file__).read_bytes()),
        'upstream_lock_sha256': sha((SOURCE / 'uv.lock').read_bytes()),
        'python': sys.version, 'packages': dict(sorted((d.metadata['Name'], d.version)
            for d in importlib.metadata.distributions())),
        'interpretation': 'Replayed published fixture calls, not observed agent trajectories; no gold labels assigned yet.'}
    (out / 'agentdojo-clean-replay.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'packages'}, indent=2))


if __name__ == '__main__':
    main()
