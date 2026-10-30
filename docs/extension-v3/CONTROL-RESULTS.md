# Task-information controls — completed arms only

The controls do not support one universal explanation. A task-versus-candidate
improvement can disappear against an empty task field, while some source/model
comparisons retain a benefit over all three controls. These are comparisons on the
same preselected subset, not comparisons against a different full-data baseline.
No prompt, model, label or threshold is selected from these outcomes.

The table gives task-weighted Brier differences: **task minus comparator**, so
negative values favor the authentic task. Each row uses the same planned examples
for all four contrasts. Complete-pair counts are shown as available/planned. The
unrounded estimates, grouped intervals, task/secondary-group counts, text-weighted
sensitivity and missing-response bounds are in `analysis/control-effects.csv`.
Classification-error effects are also in that CSV; error units are fractions,
not percentage points. Do not interpret this point-estimate table as an uncertainty
or significance summary.

## jev_firstparty

| Source | Brier pairs | Candidate | Empty field | Reminder | Scrambled task |
|---|---|---:|---:|---:|---:|
| agentdojo-clean-banking | 8/8 | +0.0023 | +0.0022 | -0.0051 | -0.0023 |
| agentdojo-clean-slack | 8/8 | +0.0041 | +0.0023 | +0.0016 | -0.0001 |
| agentdojo-clean-travel | 8/8 | +0.0006 | +0.0005 | -0.0075 | -0.0005 |
| agentdojo-clean-workspace | 8/8 | +0.0008 | +0.0006 | -0.0025 | -0.0081 |
| agentdyn-dailylife | 16/16 | +0.0043 | +0.0039 | +0.0028 | -0.0246 |
| agentdyn-github | 4/4 | +0.0065 | +0.0062 | +0.0026 | -0.0012 |
| agentdyn-shopping | 15/15 | +0.0354 | +0.0289 | +0.0205 | +0.0133 |
| injecagent-dh | 8/8 | -0.1154 | +0.0074 | +0.0951 | -0.0061 |
| injecagent-ds | 8/8 | -0.0246 | +0.0185 | +0.0693 | +0.0200 |

## luna_decisions

| Source | Brier pairs | Candidate | Empty field | Reminder | Scrambled task |
|---|---|---:|---:|---:|---:|
| agentdojo-clean-banking | 8/8 | +0.0000 | +0.0000 | +0.0000 | -0.0066 |
| agentdojo-clean-slack | 8/8 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| agentdojo-clean-travel | 8/8 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| agentdojo-clean-workspace | 8/8 | +0.0000 | +0.0000 | +0.0000 | -0.0000 |
| agentdyn-dailylife | 16/16 | -0.0000 | +0.0000 | +0.0000 | -0.0002 |
| agentdyn-github | 4/4 | -0.0001 | +0.0001 | +0.0001 | +0.0001 |
| agentdyn-shopping | 15/15 | +0.0002 | +0.0002 | +0.0002 | -0.0016 |
| injecagent-dh | 8/8 | -0.0481 | +0.0462 | -0.0246 | -0.0611 |
| injecagent-ds | 8/8 | -0.3401 | -0.3417 | -0.2898 | -0.2861 |

## laya_local

| Source | Brier pairs | Candidate | Empty field | Reminder | Scrambled task |
|---|---|---:|---:|---:|---:|
| agentdojo-clean-banking | 8/8 | +0.0017 | -0.0229 | -0.0224 | -0.0051 |
| agentdojo-clean-slack | 8/8 | +0.0365 | -0.1954 | -0.2379 | -0.1877 |
| agentdojo-clean-travel | 8/8 | +0.1053 | -0.0402 | -0.1074 | -0.1113 |
| agentdojo-clean-workspace | 8/8 | +0.2985 | -0.0265 | -0.1907 | -0.1080 |
| agentdyn-dailylife | 16/16 | -0.0642 | -0.0812 | -0.1528 | -0.1413 |
| agentdyn-github | 4/4 | -0.2638 | -0.3328 | -0.3862 | -0.0661 |
| agentdyn-shopping | 15/15 | +0.0017 | +0.0024 | -0.0011 | -0.0025 |
| injecagent-dh | 8/8 | +0.0143 | +0.0156 | +0.0157 | +0.0127 |
| injecagent-ds | 8/8 | -0.0001 | +0.0506 | +0.0541 | -0.0536 |

## nimble_local

| Source | Brier pairs | Candidate | Empty field | Reminder | Scrambled task |
|---|---|---:|---:|---:|---:|
| agentdojo-clean-banking | 8/8 | +0.0012 | +0.0013 | +0.0010 | -0.0046 |
| agentdojo-clean-slack | 8/8 | +0.0049 | +0.0049 | +0.0018 | +0.0055 |
| agentdojo-clean-travel | 8/8 | -0.0000 | +0.0000 | +0.0000 | -0.0331 |
| agentdojo-clean-workspace | 8/8 | +0.0001 | +0.0000 | -0.0000 | -0.0015 |
| agentdyn-dailylife | 16/16 | -0.0273 | -0.0260 | -0.0253 | -0.0265 |
| agentdyn-github | 4/4 | +0.0010 | +0.0014 | +0.0016 | -0.0025 |
| agentdyn-shopping | 15/15 | -0.0077 | -0.0116 | -0.0073 | -0.0131 |
| injecagent-dh | 8/8 | -0.3487 | -0.3673 | -0.2557 | -0.1056 |
| injecagent-ds | 8/8 | -0.2192 | -0.2658 | -0.1434 | -0.0955 |

## Concrete interpretations and their limits

For Jev on the eight selected InjecAgent direct-harm pairs, task-versus-candidate
Brier change is−0.1154, but task-versus-empty-field is+0.0074 and task-versus-reminder
is+0.0951. The first two crossed intervals include zero; the reminder contrast is
[+0.0290,+0.1736]. This small attack-only slice does not establish that authentic
semantic task information is responsible for the candidate-baseline improvement.
The same released fixtures and seven attack-instruction groups constrain inference.

For Luna Decisions on eight InjecAgent stealing pairs, task Brier is lower than
candidate, empty-field, reminder and scrambled conditions (−0.3401,−0.3417,−0.2898,
−0.2861). The task–scrambled interval is[−0.6565,−0.0002], illustrating its width
and proximity to zero. This bounded result is compatible with useful task
information, but is not a corrected-for-multiplicity discovery or a claim about
unseen attack families. All contrasts were predeclared; selectively highlighting
one narrow interval would overstate the evidence.

For Laya on eight clean workspace pairs, adding the task worsens Brier against
candidate alone by+0.2985, while improving it relative to the generic reminder by
−0.1907. Thus a relative control advantage can coexist with worse absolute
performance. Empty-field and scrambled comparisons have wide intervals spanning
zero. The result does not diagnose an internal mechanism or repair Laya's weak
clean-fixture performance.

Scrambling retains the task's words and can preserve partial meaning. The empty
field changes serialization without informative task content; the reminder adds
instructions and length. None is a perfect semantic-isolation experiment. Controls
are constructed information interventions on the original scenario, not authentic
historical alternative tasks with newly verified gold labels.

The banking/slack control slices have fewer than five distinct secondary groups;
GitHub has only three task groups. Their intervals are intentionally omitted.
Repeated texts and fixed templates remain correlated. No pooled control score,
model winner, threshold change or fitted calibration follows from this checkpoint.
Astra and Luna Responses must finish before final cross-model interpretation.

For Nimble, the eight direct-harm control pairs improve against candidate and
empty-field baselines (Brier −0.3487 and −0.3673), but intervals against the
reminder and scrambled task include zero. On eight stealing pairs, task minus
scrambled is −0.0955 [−0.2688,−0.0011], while task minus reminder is −0.1434
[−0.3538,+0.0513]. This is limited evidence consistent with useful task information
in one slice, not a universal mechanism or multiplicity-adjusted discovery.
