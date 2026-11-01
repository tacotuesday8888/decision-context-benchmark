"""Synthetic nonconstant randomization/bootstrap oracles; no empirical access."""
from pathlib import Path
import json
import math

import numpy as np
import independent_math as m


def run():
    # Twenty positive components and one negative component, with both classes
    # present in every component.  |statistic| >= 19/21 exactly when a sign draw
    # has at most one, or at least twenty, positive effective contributions.
    # Count sign states directly, independently of a matrix-vector statistic.
    values=[x for x in ([1.,1.]*20+[-1.,-1.])]
    groups=[f'g{i:02}' for i in range(21) for _ in range(2)]
    labels=[0,1]*21
    observed=m.infer(values,groups,labels)
    rng=np.random.default_rng(m.SEED)
    extreme=0
    for start in range(0,m.R,512):
        bits=rng.integers(0,2,size=(min(512,m.R-start),21),dtype=np.int8)
        # The known negative component reverses the last fair sign.
        effective=bits[:,:20].sum(axis=1)+(1-bits[:,20])
        extreme+=int(np.count_nonzero((effective<=1)|(effective>=20)))
    expected_p=(extreme+1)/(m.R+1)
    assert observed['randomization_p_two_sided']==expected_p
    assert observed['randomization_method']=='Monte Carlo whole-component signs, +1 correction'
    assert math.isclose(observed['estimate'],19/21)
    rng=np.random.default_rng(m.SEED+1)
    boot=[]
    for start in range(0,m.B,256):
        indexes=rng.integers(0,21,size=(min(256,m.B-start),21))
        boot.extend((1-2*np.sum(indexes==20,axis=1)/21).tolist())
    assert np.allclose(observed['interval_95'],np.quantile(boot,[.025,.975]),rtol=0,atol=1e-15)
    assert np.allclose(observed['interval_99_1667'],np.quantile(boot,[.05/12,1-.05/12]),rtol=0,atol=1e-15)
    first={'fixture':'21 nonconstant components direct sign-count and binomial bootstrap oracle',
        'point':19/21,'monte_carlo_extreme_draws':extreme,'p':expected_p,
        'interval_95':observed['interval_95'],'interval_99_1667':observed['interval_99_1667'],
        'bootstrap_draws':m.B,'randomization_draws':m.R}

    # Four heterogeneous components, two lacking a class.  Independent scalar
    # calculation recomputes each resampled class denominator directly from
    # the sampled names rather than using component multiplicity matrices.
    cells=[{0:0.,1:1.},{0:1.},{1:-1.},{0:-.5,1:.5}]
    values=[];groups=[];labels=[]
    for i,cell in enumerate(cells):
        for label,value in cell.items():
            values.append(value);groups.append(f'h{i}');labels.append(label)
    result=m.infer(values,groups,labels)
    assert math.isclose(result['estimate'],1/6)
    rng=np.random.default_rng(m.SEED+1)
    direct=[];missing=0
    for start in range(0,m.B,256):
        indexes=rng.integers(0,4,size=(min(256,m.B-start),4))
        for draw in indexes:
            classes=[[cells[int(i)][y] for i in draw if y in cells[int(i)]] for y in (0,1)]
            if not all(classes):missing+=1;continue
            direct.append(sum(math.fsum(part)/len(part) for part in classes)/2)
    assert result['bootstrap_degenerate_draws']==missing
    assert result['bootstrap_valid_draws']==len(direct)
    assert np.allclose(result['interval_95'],np.quantile(direct,[.025,.975]),rtol=0,atol=1e-15)
    assert np.allclose(result['interval_99_1667'],np.quantile(direct,[.05/12,1-.05/12]),rtol=0,atol=1e-15)
    second={'fixture':'heterogeneous missing-class scalar bootstrap oracle',
        'point':1/6,'bootstrap_degenerate_draws':missing,'bootstrap_valid_draws':len(direct),
        'interval_95':result['interval_95'],'interval_99_1667':result['interval_99_1667']}
    return {'version':'independent-math-rng-oracles-1','checks_passed':True,
        'empirical_inputs_read':False,'project_analytical_functions_imported':False,
        'fixtures':[first,second]}


if __name__=='__main__':
    report=run()
    m.immutable(Path(__file__).parent/'rng-fixture-results.json',report)
    print(json.dumps({'checks_passed':True,'fixture_count':len(report['fixtures'])}))
