"""No-inference budget/precision planning from exact v6 payloads and historical ledger."""
import collections
import json
import math
import statistics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    RAW, OUT, read, write_rows, report, rank, canonical_bytes, sha256,
)
from scripts.study_v5.feasibility import reconcile, reservation
from scripts.study_v5.prompts import conditions, native_payload

PRIMARY_CONDITIONS = ('format', 'task', 'reminder', 'length')
RATES = {'openai': .10, 'typesafe': .042}
ROUTES = {'openai': 'luna_decisions', 'typesafe': 'jev_firstparty'}
LIMITS = {'v6_total_each_provider': 12., 'primary_each_provider': 9.,
          'supporting_each_provider': 2., 'initial_development_each_provider': .5,
          'recovery_each_provider': .5}

def group_prefix(rows, budget, selected_conditions):
    """Same whole-group prefix for both native providers; no skipping costly groups."""
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['group']].append(row)
    spent = {p: 0. for p in RATES}
    selected, costs = [], []
    for group in sorted(groups, key=lambda g: rank('budget-order:' + g)):
        cost = {}
        for provider, route in ROUTES.items():
            payloads = {sha256(canonical_bytes(p)): p for row in groups[group]
                        for condition in selected_conditions(row)
                        for p in [native_payload(row, condition, route)]}
            cost[provider] = math.fsum(reservation(p, RATES[provider]) for p in payloads.values())
        if any(spent[p] + cost[p] > budget for p in spent):
            break
        selected.append(group)
        costs.append({'group': group, 'costs': cost})
        for provider in spent:
            spent[provider] += cost[provider]
    return selected, spent, costs

def main():
    rows = read(RAW / 'prepared.jsonl')
    primary = [r for r in rows if r['source'] == 'browsesafe' and r['split_proposal'] == 'confirmation']
    groups, amount, costs = group_prefix(primary, LIMITS['primary_each_provider'], lambda _: PRIMARY_CONDITIONS)
    selected = [r for r in primary if r['group'] in set(groups)]
    write_rows(RAW / 'budget-primary-proposal.jsonl', [{'id': r['id'], 'group': r['group']} for r in selected])
    write_rows(RAW / 'budget-group-costs.jsonl', costs)
    all_source_costs = {}
    for source in sorted({r['source'] for r in rows}):
        part = [r for r in rows if r['source'] == source]
        all_source_costs[source] = {provider: math.fsum(reservation(native_payload(row, condition, route), RATES[provider])
            for row in part for condition in (PRIMARY_CONDITIONS if source == 'browsesafe' else conditions(row)))
            for provider, route in ROUTES.items()}
    normal = statistics.NormalDist()
    scenarios = []
    for n in sorted({100, 200, 400, 800, len(groups)} - {0}):
        for q in [.1, .25, .5]:
            for tests in [1, 6]:
                z = normal.inv_cdf(1 - .05 / (2 * tests))
                scenarios.append({'independent_units': n, 'assumed_discordance': q,
                    'comparison_count': tests, 'approx_80pct_power_delta_pp': 100 * (z + normal.inv_cdf(.8)) * math.sqrt(q/n),
                    'approx_simultaneous_95_halfwidth_pp': 100 * z * math.sqrt(q/n)})
    lengths = sorted(len(r['candidate'].encode()) for r in rows if r['source'] == 'browsesafe')
    output = {'version': 'v6-feasibility-1', 'accounting': reconcile(), 'new_inference_spend': 0,
              'limits_proposed_for_Sol': LIMITS, 'rates_per_million_planning_only': RATES,
              'primary_conditions': list(PRIMARY_CONDITIONS),
              'full_source_pool_cost_envelopes': all_source_costs,
              'browse_candidate_bytes': {'min': min(lengths), 'median': statistics.median(lengths),
                  'p95': lengths[math.ceil(.95 * len(lengths))-1], 'max': max(lengths)},
              'provisional_confirmation_groups_before_budget': len({r['group'] for r in primary}),
              'budget_prefix_groups': len(groups), 'budget_prefix_rows': len(selected),
              'budget_prefix_envelope_usd': amount, 'precision_scenarios': scenarios,
              'zero_FP_one_sided_95_upper_if_independent_benign_groups': 1-.05**(1/len(groups)) if groups else None,
              'reservation_definition': '2 * (serialized UTF-8 bytes + 4096) * base rate / 1e6; conservative planning proxy, not a tokenizer bound',
              'not_execution_ready': True,
              'limitations': ['Labels/group review/overlap/coverage can reduce counts.',
                  'Prices and all subsequent accounting must be checked before dispatch.',
                  'No probabilities or outcomes used for cohort selection.',
                  'Normal scenarios do not model actual group means or establish achieved power.']}
    report(OUT / 'feasibility.json', output)
    print(json.dumps({k: output[k] for k in ['browse_candidate_bytes', 'provisional_confirmation_groups_before_budget',
                                           'budget_prefix_groups', 'budget_prefix_rows', 'budget_prefix_envelope_usd']}))

if __name__ == '__main__':
    main()
