"""Synthetic-only checks of v7's actual t/Holm and whole-group intervals.

No model, credential, network, source text or empirical predictions are used.
The generated binary errors are coherent: three controls share each model's task
errors and every group contains a clean/attack pair. Missing errors stay missing.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import scipy
from scipy.stats import norm

from scripts.study_v7.analysis import BOOTSTRAP_DRAWS, SEED, _seed, bootstrap_mean, holm, paired_t


def rate_interval(successes, trials):
    """Wilson 95% Monte Carlo interval (uncertainty over simulated repetitions)."""
    if not trials:
        return {"successes": 0, "trials": 0, "rate": None, "mc_95": None}
    p, z = successes/trials, float(norm.ppf(.975))
    denominator = 1+z*z/trials
    center = (p+z*z/(2*trials))/denominator
    radius = z*np.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))/denominator
    return {"successes": int(successes), "trials": int(trials), "rate": p,
            "mc_95": [max(0., float(center-radius)), min(1., float(center+radius))]}


def generate_errors(rng, n, *, shape="symmetric", q=.5, effect=0.):
    """Return group x model x condition(task,3controls) x page binary errors.

    Symmetric family: D is in {-1,0,1}, P(D!=0)=q, E[D]=effect,
    SD=sqrt(q-effect**2). Shared task errors create within-model dependence.
    Skewed family: D is -.5 or +1 with probabilities 2/3 and 1/3 at null,
    optionally zeroed independently per control with probability 1-q. The
    positive branch probability is (effect/q+.5)/1.5, so E[D]=effect.
    Models are independent; the three contrasts within a model share a sign.
    """
    errors = np.empty((n, 2, 4, 2), dtype=np.int8)
    if q <= 0 or q > 1 or abs(effect) > q:
        raise ValueError("Invalid bounded distribution")
    for model in range(2):
        if shape == "symmetric":
            positive = rng.random(n) < (1+effect/q)/2
            task = (~positive).astype(np.int8)
            errors[:, model, 0, :] = task[:, None]
            for control in range(1, 4):
                flip = rng.random(n) < q
                control_error = np.where(flip, 1-task, task)
                errors[:, model, control, :] = control_error[:, None]
        elif shape == "skewed":
            positive_probability = (effect/q+.5)/1.5
            if not 0 <= positive_probability <= 1:
                raise ValueError("Invalid skewed effect")
            positive = rng.random(n) < positive_probability
            # Negative branch has task pair mean .5; positive has task mean 0.
            errors[:, model, 0, 0] = 0
            errors[:, model, 0, 1] = (~positive).astype(np.int8)
            for control in range(1, 4):
                change = rng.random(n) < q
                errors[:, model, control, :] = errors[:, model, 0, :]
                errors[change, model, control, :] = positive[change, None].astype(np.int8)
        else:
            raise ValueError("Unknown synthetic distribution")
    return errors


def group_differences(errors):
    pair_means = errors.mean(axis=-1)
    return (pair_means[:, :, 1:] - pair_means[:, :, :1]).reshape(len(errors), 6)


def missing_mask(rng, errors, missingness):
    if missingness == "none":
        return np.ones_like(errors, dtype=bool)
    if missingness == "mcar_cells":
        # 0.3% missing individual outputs -> roughly 9% shared-group attrition.
        return rng.random(errors.shape) >= .003
    if missingness == "informative":
        # Deliberately unfavorable outcome-related missingness; no guarantee
        # of unbiased complete cases is claimed. All retained errors inform bounds.
        d = group_differences(errors)
        positive = np.any(d > 0, axis=1)
        mask = np.ones_like(errors, dtype=bool)
        mask[:, 0, 0, 1] = rng.random(len(errors)) >= np.where(positive, .35, .02)
        return mask
    raise ValueError("Unknown missingness mechanism")


def masked_bounds(errors, mask):
    lower = np.where(mask, errors, 0.)
    upper = np.where(mask, errors, 1.)
    # Control minus task extrema keep every known individual error.
    low = lower[:, :, 1:, :].mean(axis=-1) - upper[:, :, :1, :].mean(axis=-1)
    high = upper[:, :, 1:, :].mean(axis=-1) - lower[:, :, :1, :].mean(axis=-1)
    return low.reshape(len(errors), 6).mean(axis=0), high.reshape(len(errors), 6).mean(axis=0)


def scenario(spec, *, repetitions=1000, interval_repetitions=1000,
             bootstrap_draws=BOOTSTRAP_DRAWS, seed=SEED):
    """Use the production t/Holm and bootstrap functions in every repetition."""
    if interval_repetitions > repetitions or repetitions < 1 or interval_repetitions < 1:
        raise ValueError("Require 1 <= interval repetitions <= repetitions")
    name = spec["name"]
    rng = np.random.default_rng(_seed(seed, name))
    reject = np.zeros(6, dtype=int)
    any_reject = all_reject = 0
    point_cover = conservative_cover = np.zeros(6, dtype=int)
    point_cover, conservative_cover = point_cover.copy(), conservative_cover.copy()
    simultaneous_point = simultaneous_conservative = bounds_cover = 0
    omitted_draws = 0
    mean_bias = np.zeros(6)
    complete_n = []
    for iteration in range(repetitions):
        errors = generate_errors(rng, spec["groups"], shape=spec["shape"], q=spec["q"], effect=spec["effect"])
        ds = group_differences(errors)
        mask = missing_mask(rng, errors, spec["missingness"])
        common = mask.all(axis=(1, 2, 3))
        complete_n.append(int(common.sum()))
        selected = ds[common]
        tests = [paired_t(selected[:, contrast]) for contrast in range(6)]
        decisions = np.asarray([r["reject"] for r in holm([test["p"] for test in tests])])
        reject += decisions
        any_reject += int(decisions.any())
        all_reject += int(decisions.all())
        mean_bias += selected.mean(axis=0)-spec["effect"] if len(selected) else 0
        lower, upper = masked_bounds(errors, mask)
        finite_target = ds.mean(axis=0)
        bounds_cover += int(np.all(lower-1e-12 <= finite_target) and np.all(finite_target <= upper+1e-12))
        if iteration < interval_repetitions:
            covered_point, covered_conservative = [], []
            for contrast in range(6):
                interval = bootstrap_mean(selected[:, contrast], draws=bootstrap_draws,
                    seed=f"{seed}/{name}/{iteration}/{contrast}")
                omitted_draws += interval["omitted_draws"]
                ci, adjusted_ci = interval["pointwise_95"], interval["conservative_six_99_166667"]
                covered_point.append(bool(ci is not None and ci[0] <= spec["effect"] <= ci[1]))
                covered_conservative.append(bool(adjusted_ci is not None and adjusted_ci[0] <= spec["effect"] <= adjusted_ci[1]))
            point_cover += covered_point
            conservative_cover += covered_conservative
            simultaneous_point += int(all(covered_point))
            simultaneous_conservative += int(all(covered_conservative))
    return {**spec, "repetitions": repetitions, "interval_repetitions": interval_repetitions,
        "bootstrap_draws_per_interval": bootstrap_draws, "bootstrap_omitted_draws": omitted_draws,
        "shared_complete_groups_mean": float(np.mean(complete_n)), "shared_complete_groups_range": [min(complete_n), max(complete_n)],
        "complete_case_bias_by_contrast": (mean_bias/repetitions).tolist(),
        "family_any_rejection": rate_interval(any_reject, repetitions),
        "family_all_rejection": rate_interval(all_reject, repetitions),
        "contrast_rejection": [rate_interval(int(r), repetitions) for r in reject],
        "pointwise_95_coverage": [rate_interval(int(r), interval_repetitions) for r in point_cover],
        "conservative_99_166667_coverage": [rate_interval(int(r), interval_repetitions) for r in conservative_cover],
        "pointwise_all_six_coverage": rate_interval(simultaneous_point, interval_repetitions),
        "conservative_all_six_coverage": rate_interval(simultaneous_conservative, interval_repetitions),
        "all_planned_bounds_contain_realized_full_group_means": rate_interval(bounds_cover, repetitions)}


def specifications():
    specs = []
    # Exact planned 3,000 groups, plus the descriptive 500-group comparator scale.
    for n in (500, 3000):
        for shape, q in (("symmetric", .5), ("skewed", 1.)):
            specs.append({"name": f"{shape}-null-n{n}", "groups": n, "shape": shape, "q": q,
                          "effect": 0., "missingness": "none"})
    # Planning sensitivity at the actual target, not achieved/observed power.
    for q in (.25, .5, 1.):
        for effect in (.03, .05):
            specs.append({"name": f"symmetric-alternative-q{q}-effect{effect}", "groups": 3000,
                          "shape": "symmetric", "q": q, "effect": effect, "missingness": "none"})
    specs.append({"name": "skewed-alternative-effect0.05", "groups": 3000, "shape": "skewed", "q": 1., "effect": .05, "missingness": "none"})
    for mechanism in ("mcar_cells", "informative"):
        for effect in (0., .05):
            specs.append({"name": f"skewed-{mechanism}-effect{effect}", "groups": 3000,
                          "shape": "skewed", "q": 1., "effect": effect, "missingness": mechanism})
    return specs


def run(*, repetitions=1000, interval_repetitions=1000, draws=BOOTSTRAP_DRAWS, seed=SEED):
    started = time.monotonic()
    outcomes = []
    for spec in specifications():
        outcomes.append(scenario(spec, repetitions=repetitions, interval_repetitions=interval_repetitions,
                                 bootstrap_draws=draws, seed=seed))
        print(f"Synthetic check complete: {spec['name']}", flush=True)
    return {"version": "study-v7-synthetic-procedure-check-v1", "synthetic_only": True,
            "model_calls": 0, "seed": seed, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__,
            "elapsed_seconds": time.monotonic()-started, "scenarios": outcomes,
            "interpretation": [
                "Every repetition calls the production two-sided paired group-mean t/Holm6 functions; reported null any-rejection is familywise Type I error.",
                "Every interval repetition calls the production 20,000-draw whole-group percentile interval function. Empirical multinomial compression is distributionally identical to group-index resampling.",
                f"Tests use {repetitions} repetitions and interval coverage uses {interval_repetitions}, each with six {draws}-draw intervals. Wilson intervals show the resulting Monte Carlo uncertainty.",
                "Symmetric planning differences have SD sqrt(q-effect^2), near 0.5, 0.7071 and 1.0; controls share task errors within each model. Skewed differences are bounded on {-0.5,0,1}.",
                "Informative missingness is an intentional sensitivity stress, not a validity target; complete-case inference can be biased. All-planned bounds retain known errors and target the finite planned cohort.",
                "Finite synthetic checks do not prove independence, interval coverage or Type I control for every source population. Pointwise 95% intervals do not claim simultaneous 95% coverage; conservative six-comparison intervals are separate.",
                "Alternative rejection rates are prospective assumed-distribution power, not observed/achieved power or an empirical model result."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/study-v7/statistical-simulation.json"))
    parser.add_argument("--repetitions", type=int, default=1000)
    parser.add_argument("--interval-repetitions", type=int, default=1000)
    parser.add_argument("--draws", type=int, default=BOOTSTRAP_DRAWS)
    args = parser.parse_args()
    result = run(repetitions=args.repetitions, interval_repetitions=args.interval_repetitions, draws=args.draws)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
