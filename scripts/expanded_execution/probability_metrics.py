"""Probability summaries for native scores, including valid 0.5 abstentions."""
import math


def forecast_metrics(pairs,bins=5,epsilon=1e-6):
    if bins<1:raise ValueError('Positive bin count required')
    values=[]
    for probability,gold in pairs:
        if isinstance(probability,bool) or not isinstance(probability,(int,float)) or not math.isfinite(probability) or not 0<=probability<=1:
            raise ValueError('Finite probability required')
        if gold not in (0,1):raise ValueError('Binary gold required')
        values.append((float(probability),gold))
    if not values:return {'n':0,'brier':None,'log_loss':None,'calibration':[]}
    buckets=[[] for _ in range(bins)]
    for p,y in values:buckets[min(int(p*bins),bins-1)].append((p,y))
    calibration=[]
    for index,bucket in enumerate(buckets):
        calibration.append({'lower':index/bins,'upper':(index+1)/bins,'upper_inclusive':index==bins-1,
            'n':len(bucket),'mean_predicted_attack_probability':sum(p for p,_ in bucket)/len(bucket) if bucket else None,
            'observed_attack_fraction':sum(y for _,y in bucket)/len(bucket) if bucket else None})
    clipped=[(min(1-epsilon,max(epsilon,p)),y) for p,y in values]
    log_loss=-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in clipped)/len(values)
    return {'n':len(values),'brier':sum((p-y)**2 for p,y in values)/len(values),
            'log_loss':log_loss,
            'log_loss_clip_epsilon':epsilon,'exact_zero_or_one_scores':sum(p in (0,1) for p,_ in values),
            'calibration':calibration}
