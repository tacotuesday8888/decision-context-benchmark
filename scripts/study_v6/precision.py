"""Prespecified planning simulation, not experiment results or achieved study power."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import OUT, report

def main():
    import numpy as np
    import scipy
    from scipy.stats import binom
    f = json.loads((OUT / 'feasibility.json').read_text())
    rng = np.random.default_rng(20261030)
    result = []
    repetitions = 20000
    for n in sorted({200, 400, 800, 1210, f['budget_prefix_groups']} - {0}):
        for q in [.1, .25, .5]:
            for delta in [.05, .10]:
                # One paired binary contrast per independent unit: +1 improvement,
                # -1 regression, 0 concordance; not a synthetic semantic dataset.
                samples = rng.multinomial(n, [(q + delta)/2, (q - delta)/2, 1-q], size=repetitions)
                discordant = samples[:, 0] + samples[:, 1]
                smaller = np.minimum(samples[:, 0], samples[:, 1])
                pvalues = np.minimum(1, 2 * binom.cdf(smaller, discordant, .5))
                for comparisons in [1, 6]:
                    power = float(np.mean(pvalues <= .05 / comparisons))
                    result.append({'independent_units': n, 'discordance': q, 'true_error_reduction': delta,
                        'comparisons_bonferroni': comparisons, 'estimated_power': power,
                        'monte_carlo_standard_error': float((power * (1-power)/repetitions)**.5)})
    report(OUT / 'precision-scenarios.json', {'seed': 20261030, 'repetitions_per_scenario': repetitions,
        'numpy_version': np.__version__, 'scipy_version': scipy.__version__, 'scenarios': result,
        'new_model_calls': 0,
        'interpretation': 'Exact conditional paired-binomial planning for independent binary units, conservative Bonferroni family. Not achieved power of clustered balanced error; actual dependence/review/coverage may reduce information.'})
    print(json.dumps({'planning_scenarios': len(result), 'model_calls': 0}))

if __name__ == '__main__':
    main()
