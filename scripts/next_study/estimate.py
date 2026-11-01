"""Offline planning arithmetic only: no network, credentials, models, or raw predictions.

Run from the repository root: python3 scripts/next_study/estimate.py
The printed JSON is a forecast, not an empirical result or an execution permission.
"""
import json
import math
from decimal import Decimal as D
from statistics import NormalDist


def money(value):
    return str(value.quantize(D("0.000001")))


def forecast():
    million = D(1_000_000)
    counts = {
        "jev": {"main": 24000, "main_dev": 400, "repeat": 800, "external": 4000, "external_dev": 100, "audit": 0},
        "luna_decisions": {"main": 24000, "main_dev": 400, "repeat": 800, "external": 4000, "external_dev": 100, "audit": 0},
        "luna_responses": {"main": 4000, "main_dev": 400, "repeat": 400, "external": 1000, "external_dev": 100, "audit": 0},
        "sol_responses": {"main": 4000, "main_dev": 400, "repeat": 400, "external": 1000, "external_dev": 100, "audit": 100},
        "protectai_local": {"main": 1000, "main_dev": 100, "repeat": 0, "external": 4000, "external_dev": 100, "audit": 0},
    }
    for row in counts.values():
        row["total"] = sum(row.values())
    assert counts["jev"]["total"] == 29300
    assert counts["sol_responses"]["total"] == 6000
    assert sum(counts[k]["total"] for k in counts if k != "protectai_local") == 70500
    assumptions = {
        "main_jev_input_tokens": "7195.29",
        "main_openai_input_tokens": "6013.45",
        "external_input_tokens": "400",
        "luna_mean_output_tokens": 16,
        "sol_mean_output_tokens": 128,
        "audit_mean_output_tokens": 512,
        "luna_max_output_tokens": 256,
        "sol_max_output_tokens": 2048,
        "audit_max_output_tokens": 2048,
        "inputs": "Main means are usage-only v6 estimates. External and Sol/audit output means are assumptions. Audit includes both pages per call.",
    }
    rates = {
        "jev_input": "0.042", "luna_input": "0.10", "luna_decisions_max_write": "0.25",
        "luna_output": "0.50", "sol_input": "2", "sol_output": "10",
    }
    input_tokens = {}
    for name in ("jev", "luna_decisions", "luna_responses", "sol_responses"):
        row = counts[name]
        main_n = row["main"] + row["main_dev"] + row["repeat"]
        main_mean = D(assumptions["main_jev_input_tokens"] if name == "jev" else assumptions["main_openai_input_tokens"])
        input_tokens[name] = main_n * main_mean + (row["external"] + row["external_dev"]) * D("400")
        input_tokens[name] += row["audit"] * D(assumptions["main_openai_input_tokens"]) * 2

    def cost_scenario(input_multiplier, native_write, maximum_outputs):
        scale = D(str(input_multiplier)) / million
        out_luna = counts["luna_responses"]["total"] * (256 if maximum_outputs else 16)
        out_sol = 5900 * (2048 if maximum_outputs else 128) + 100 * (2048 if maximum_outputs else 512)
        costs = {
            "jev": input_tokens["jev"] * scale * D(rates["jev_input"]),
            "luna_decisions": input_tokens["luna_decisions"] * scale * D(rates["luna_decisions_max_write"] if native_write else rates["luna_input"]),
            "luna_responses": input_tokens["luna_responses"] * scale * D(rates["luna_input"]) + D(out_luna) / million * D(rates["luna_output"]),
            "sol_responses_including_audit": input_tokens["sol_responses"] * scale * D(rates["sol_input"]) + D(out_sol) / million * D(rates["sol_output"]),
        }
        costs["openai_total"] = sum(v for k, v in costs.items() if k != "jev")
        costs["all_test_total"] = costs["openai_total"] + costs["jev"]
        return {k: money(v) for k, v in costs.items()}

    normal = NormalDist()
    alpha = .05 / 6
    zcrit = normal.inv_cdf(1 - alpha / 2)
    zpower = normal.inv_cdf(.8)
    planning = []
    for n in (487, 500, 2000, 3000):
        for sd in (.5, math.sqrt(.5), 1.):
            for delta in (.03, .05):
                shift = delta * math.sqrt(n) / sd
                power = 1 - normal.cdf(zcrit - shift) + normal.cdf(-zcrit - shift)
                planning.append({
                    "groups": n, "assumed_group_difference_sd": round(sd, 8),
                    "true_mean_error_reduction": delta,
                    "normal_approx_power_per_contrast_bonferroni6": round(power, 6),
                    "approx_n_for_80percent": math.ceil(((zcrit + zpower) * sd / delta) ** 2),
                })

    historical_oa, historical_jev = D("7.02755920"), D("1.827584934")
    ordinary = cost_scenario(1, False, False)
    write_allowance = cost_scenario(1, True, False)
    stress = cost_scenario(2, True, True)
    assert D(ordinary["all_test_total"]) < D(write_allowance["all_test_total"]) < D(stress["all_test_total"])
    assert D(stress["openai_total"]) < D("350")
    assert D(stress["jev"]) < D("20")
    return {
        "version": "v7-planning-only-20261101", "inference_calls_made": 0,
        "paid_execution_authorized": False,
        "counts": counts, "assumptions": assumptions, "rates_usd_per_million": rates,
        "forecast_input_tokens": {k: str(v) for k, v in input_tokens.items()},
        "ordinary_input_forecast": ordinary,
        "native_all_12h_write_forecast": write_allowance,
        "stress_2x_input_and_all_chat_max_output": stress,
        "stress_is_certified_maximum": False,
        "proposed_incremental_caps_usd": {"openai_tests_and_audit": "350", "openai_optional_authoring": "25", "typesafe": "20", "total": "395"},
        "historical_conservative_accounting_usd": {"openai": str(historical_oa), "typesafe": str(historical_jev)},
        "existing_authorized_headroom_usd": {"openai": str(D("15") - historical_oa), "typesafe": str(D("20") - historical_jev)},
        "proposed_cumulative_caps_if_approved_usd": {"openai": str(historical_oa + D("375")), "typesafe": str(historical_jev + D("20"))},
        "runtime": {"historical_native_requests": 7904, "historical_minutes": 49.6, "projected_native_hours": round(58600 / 7904 * 49.6 / 60, 3), "paid_sol_throughput_verified": False, "target_project_hours": 20},
        "power_interpretation": "Normal approximation under explicit fixed SD assumptions; not exact t/Holm simulation, achieved power, or guarantee of independence. Highest SD1 is a conservative range endpoint for bounded D, not an asserted data distribution. Validate actual tests under symmetric/skewed nulls before execution.",
        "power_scenarios": planning,
        "sources": [
            "https://developers.openai.com/api/docs/pricing",
            "https://developers.openai.com/api/docs/guides/decisions#pricing-and-availability",
            "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
            "https://developers.openai.com/api/docs/guides/prompt-caching",
            "https://docs.typesafe.ai/models",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(forecast(), indent=2, sort_keys=True))
