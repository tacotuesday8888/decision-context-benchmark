# Prioritized next-run handoff — proposed, not executed

This checkpoint completes a bounded frozen experiment, not the larger research
program. The owner intends another run. No new inference, examples, labels,
calibration or paid scope was started for this handoff. Available funding should
support useful evidence; low spend is not an achievement or a reason to avoid
Astra. Conversely, repeating the same fixtures cannot add independent tasks.

## What we learned that changes the next experiment

1. Context effects depend on source and interface. Astra's direct-harm misses fall
   36/129→8/129; Luna Responses improves but still misses103/128 valid task examples.
   Relative improvement and adequate absolute detection are different claims.
2. The candidate-only baseline is insufficient. Jev's direct-harm probability gain
   disappears against empty-field/reminder controls; Astra's eight-pair direct-harm
   gain disappears against reminder/scrambled tasks. Give controls enough independent
   task groups instead of spending most calls on additional variants of familiar attacks.
3. Construction labels need a semantic audit. Clean/default fixtures can contain
   competing instructions or keyword-heavy content. Do not make Astra the gold
   annotator or reinterpret its agreement as correctness.
4. More calls are not more independent evidence: v3 has761 task/text pairs,
   582 texts,138 tasks and11,387 confirmation attempts. Shared templates and the
   three-task GitHub stratum constrain generalization. Laya's weak scores remain
   evidence, not a reason to discard that arm after seeing outcomes.

## Primary-source checks and their implications

Checked on2026-10-30; these are preprints/released artifacts, not assumed accepted
papers. The detailed pinned-artifact audit remains in RESEARCH-COMPARISON.md.

- [Passing the Test You Trained On](https://arxiv.org/abs/2610.03448) and its
  [current repository](https://github.com/lzwhehe/benign-instruction-bench) study
  tool-output false alarms, domain transfer and task-aware judges. Its current
  README differs from cached search summaries and the first paper version; use
  pinned code/score versions. This supports authentic tool-output coverage and
  source-specific evaluation. Our prior code inspection found task-aware/no-task
  and formatting analyses already exist; those are not our novelty claim.
- [System One reliability study](https://arxiv.org/html/2609.33401v1) separates
  classification, calibration and selected decision policies, with held-out policy
  confirmation. That supports a later development-only calibration experiment,
  not retrospectively calibrating v3 outcomes or treating lower Brier as calibrated safety.
- [CAD](https://arxiv.org/html/2608.05430v1) includes query/surrounding-response
  ablations and agent-level attack/utility evaluation. It supports preserving the
  distinction between static detection and prevention; it does not justify importing
  generated training examples into our authentic confirmation collection.
- [Decision Hijacking](https://arxiv.org/abs/2609.28613) evaluates typed action
  choices under injection, rather than only an injection detector's binary label.
  This is an adjacent prevention/decision-integrity direction. This refresh verified
  the primary abstract, not its full released artifact; do not treat it as a reproduced
  result or a ready-to-import dataset. Artifact inspection is required before use.

## First priority: better independent tasks and label evidence

Start with the already inspected benign-instruction-bench/AgentDojo and tau-bench
source pathways, then inspect suitable additional released domains. Do not assume
that a simulator's private goal string is an authentic message seen by its assistant.
Require the actual recorded user instruction and exact associated tool response,
a redistributable license, and a defensible existing label. Keep failed replay tasks
and ambiguous task/response matches excluded with receipts.

Build a human-review packet for ambiguous benign/injected cases using existing
published records only, with source/task/attack provenance and the intended policy.
Two reviewers should independently distinguish construction label from semantic
injection label, record disagreements, and adjudicate before the new confirmation
freeze. This requires human input; do not simulate reviewers or generate gold with AI.
Existing independently human-adjudicated published labels could substitute if their
meaning and provenance match. Keep v3 labels immutable.

Planning target:100 development and400 fresh confirmation task/text pairs, with at
least120 new confirmation task groups across at least three domains where feasible.
This is not a quota: publish actual eligible counts and report a shortfall rather
than fabricate context or add repeated variants. Group tasks, candidate duplicates,
attack instructions/templates and related documents across partitions. v3 outcomes
cannot become a new blind test set; all exposed groups must be tracked.

At40 approximately independent task units per source and discordance0.25, a rough
95% paired-effect half-width is1.96*sqrt(0.25/40)=15.5 percentage points, before
additional dependence. This still will not establish tiny effects. A claim of1%
false-positive rate needs far more independent benign evidence: even zero errors
needs about299 independent trials for a one-sided95% binomial upper bound near1%,
and repeated documents/tasks invalidate naive use of that count. Do not advertise
1%-FPR deployment validation from a small grouped benign set.

## Second priority: make the control comparison adequately informative

Apply candidate/task/empty-field/reminder/scrambled conditions to every newly
selected confirmation pair, rather than eight-task slices. Retain the current seven
configurations if access remains verified: six contextual routes plus candidate-only
ProtectAI. Astra remains the strong reference; report its actual calls and reported
input/output/reasoning usage, even on the zero-incremental-charge subscription route.
Do not remove Laya or any other weak arm just to improve the story.

The primary contrast should explicitly test authentic task versus the generic
reminder and empty-field baselines, with task-versus-candidate as the linked reference.
Scrambling remains an imperfect control, not a new authentic alternative task.
Define source-specific estimands, planned subgroup counts, paired failure bounds
and grouped uncertainty before inference. No post-confirmation prompt or threshold
selection. Source-specific absolute miss/false-alarm rates accompany all effects.

For the planning target above, five conditions on500 pairs gives2,500 calls per
contextual configuration (15,000 across six), plus500 specialist scans:15,500 calls,
of which12,400 are confirmation and3,100 development. These are proposed request
counts, not experiments already performed or15,500 independent examples.

## Third priority: calibration or prevention only as separate hypotheses

If probability reliability is the next question, choose one simple calibration
method on separate development groups, freeze it, and compare native versus
calibrated proper scores on fresh confirmation. Do not tune thresholds and call the
same evaluation a calibrated safety demonstration. A low-FPR allow/block/escalate
policy needs its own adequately powered policy-selection/confirmation design.

If prevention is prioritized instead, first validate one offline sandbox and its
attacker-success and legitimate-task-completion criteria. Then freeze a small
agent experiment with genuine task histories and actual executions. Our clean replay
and current static detector scores do not establish that feasibility or prevention.
Do not launch both directions merely to consume unused allowance.

## Bounded execution and budget handoff

Current conservative all-in metered accounting:OpenAI$0.2896254 and
TypeSafe$0.154397208, leaving$14.7103746/$19.845602792 under the existing$15/$20
caps. These are accounting headroom, not verified balances. Astra confirmation
actually attempted1,771 calls, with786,259 input and40,965 output tokens reported by
1,768 completed responses; failed-call usage is unknown. Subscription fees are
excluded, not equivalent to free unlimited access.

For2,500 calls per paid contextual configuration, scaling v3's conservative
payload reservation bounds gives roughly$2.90 OpenAI/$1.22 TypeSafe before any
new payload-size differences. A proposed additional allocation of$4/$2 fits the
existing all-in caps, but must be recomputed from actual frozen payloads/current
pricing and include bounded failures before execution. No new card, subscription,
recharge, rental or reseller fallback. A larger justified run can use remaining
authorized headroom after concrete scope/cost review; there is no higher cap yet.

Next-run order:source/label audit → grouped manifest and precision estimate → exact
prompt/settings and budget freeze → bounded development → frozen confirmation →
independent checks and report. The first gate is data validity and independent task
coverage, not payment or more model hunting. The owner plans the next run; this
handoff is the concrete starting point, not a silently started extension.

The budget above retains the authorized subscription routes for Luna chat and Astra.
It does not price paid Astra API-key inference at zero. Subscription use remains
authorized; no API-only migration or extra paid access check is planned. Exact
requests, raw responses, usage, model identifiers and hashes provide traceability
without claiming separate physical model instances.
