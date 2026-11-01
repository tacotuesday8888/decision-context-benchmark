# Subscription follow-up recommendation

November 1, 2026. **Preparation only; no new inference is authorized by this note.**
This follow-up is separate from the closed v7 delivery at `73d7a8a8` and private
[PR14](https://github.com/tacotuesday8888/decision-context-benchmark/pull/14).
Its results, accounting, stop seal, missing cells and original analysis stay frozen.
The companion [route assessment](../../results/subscription-followup/route-assessment-2026-11-01.json)
records sanitized local observations, source hashes and proposed counts. No access
token, identity claim or raw source text is exported.

## What is available and what remains uncertain

The existing project integration uses a currently documented subscription route:
project-authorized OAuth with `chatgpt.tokens.use.direct`, then public
`POST https://api.openai.com/v1/responses`. Official documentation names
`gpt-6.1-sol` in its example. This is distinct from using a signed-in Codex chat,
Codex's backend transport, or an API key. Current account-specific model discovery
must use the selected connection; a cached Codex catalog is insufficient.
See [models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

The project previously verified authentication and Sol catalog visibility at
06:19 UTC. The revised subscription configuration subsequently produced **499 valid
development classifications and 70 valid audit reviews**. Those are genuine
historical inference results, not confirmation results. Sol has **zero confirmation
and zero repeated classifications** in the delivered run.

The saved access token expired at **08:17:49 UTC / 03:17:49 EST** on November 1,
according to its saved expiry metadata. The connection retains a refresh credential
and the recorded direct-use scope. This pass did not renew credentials, issue a
catalog request, or call a model. Current authentication, model entitlement,
inference health, quota and reset timing therefore remain **unverified**. A working
subscription-backed engineering chat does not establish any of those properties
for this separately registered project connection.
The token expired after the recorded service failures; its current expiry does
not explain those earlier failures.

## Why the earlier Sol attempt stopped

These were different problems, preserved separately:

1. Four initial development calls returned HTTP400 because `prompt_cache_options`
   was unsupported. A documented pre-confirmation amendment omitted that field;
   the historical failures were retained. The route also does not support an
   explicit `max_output_tokens`, so the configuration never claimed the API
   comparator's fixed output cap.
2. Revised development returned one HTTP503 with
   `subscription_sharing_user_unavailable`. One bounded continuation sent only
   eight previously unsent cases, all successful; it did not retry the failed case.
3. The audit later returned HTTP504 with Retry-After120 after 70 valid reviews.
   This triggered the frozen repeated-service-failure rule. The remaining 29
   reviews, all Sol confirmation cases and all Sol repeats were deferred.

The evidence supports an operational service failure, not a finding that Sol
cannot classify these inputs or that its subscription quota was exhausted. The
official [error guidance](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
describes the recorded 503 code as temporary user/workspace unavailability. It
does not establish that the service has recovered now or identify the cause of
the later 504. Retained evidence is in the v7
[parameter failure](../../results/study-v7/subscription-failure-v7.0.2.json),
[service continuation](../../results/study-v7/service-recovery-v7.0.3.json) and
[audit validation](../../results/study-v7/audit-validation-v7.0.3.json) receipts.

## Smallest useful general-model follow-up

Recommend **one Sol subscription configuration on the existing locked 500-group
general subset**, with no new model search or external-source expansion in this
step. It supplies the missing general-model comparison with native Jev and Luna
on the same cases and reveals whether its task-context tradeoff differs.

| Proposed component | New calls | Purpose |
|---|---:|---|
| Fixed synthetic and development preflight | At most 10 | Check current route, full inputs and exact settings; excluded from analysis |
| 500 groups × two pages × four conditions | 4,000 | Sol first outcomes, matched to archived native outcomes |
| Locked 50 repeat groups × two pages × four conditions | 400 | A separate fresh repeat for Sol stability |
| **Maximum including preflight** | **4,410** | No API-key fallback; finite subscription allowance |

The preflight maximum comprises two fixed synthetic canaries and one complete
existing development group under all four conditions (eight classifications).
They never enter the follow-up comparison or replace a failed evaluation case.

The main selection lock is
`a45c8ac045e14dcdb4e923f76a0929556ad59144747431c723e4760f7391ea39`.
General and repeat groups were chosen before v7 results; preserve their complete
membership and rank order. Selection and request-plan hashes are in the companion
assessment. Do not pick easier cases, replace failures, or fill the old run's
unattempted cells. This is a new follow-up informed by observed v7 results, not
another untouched confirmatory sample.

Before a separately authorized execution, renew the **existing** project grant
in place through its supported refresh flow, then obtain a fresh account-specific
catalog. Preserve `gpt-6.1-sol`; if unavailable, defer rather than substitute.
Confirm available included plan allowance and the applicable app limit. Neither
catalog visibility nor zero API-dollar accounting proves unlimited included use.
No purchase, new grant, paid fallback or billing change is part of this proposal.

Freeze a new plan, namespace, output directory, accounting journal and deadline.
Explicitly select `configuration_revision="v7.0.2"` when reconstructing payloads;
the legacy default still includes the rejected cache option. Use that historically
validated Sol payload: low reasoning, strict Boolean
schema, complete stateless input, `store:false`, `stream:true`, default service
tier, no explicit output cap and no cache-control request. The documented
[preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
still list `max_output_tokens` as unsupported; cache-control omission is based on
the actual retained HTTP400. Keep the historical 500,000-token conservative
capacity bound, require fresh catalog capacity to cover all frozen inputs, and
record catalog changes rather than inheriting the API's different capacity.
Provider-default output and caching remain uncontrolled and disclosed. Use
sequential requests initially;
record requested/returned model and settings, terminal events, usage, IDs, hashes,
timestamps and partial responses. Success requires `response.completed` plus the
valid schema. A service/quota failure stops new admissions, preserves the failed
outcome and leaves planned missing cells; it does not trigger route changes or
case replacement. The new instruction must bound wall time and included usage.
For planning only, the 499 successful development calls averaged 3.24 seconds
(median 2.82; 95th percentile 5.64). At that historical mean, 4,410 sequential calls
would take about four hours before interruptions. A proposed five-hour wall cap
would leave limited recovery margin and could still end incomplete; it is not a
current authorization or a service forecast.

Report Sol control-minus-task balanced-error contrasts (positive favors task),
FPR, FNR, balanced error, coverage and
whole-group intervals. Match native comparisons within this fixed subset and
publish each actual denominator/cohort hash. Preserve missing-outcome bounds and
separate repeat disagreement. Treat this follow-up descriptively; do not append
tests to the closed six-test Holm family or pool it with the original primary
cohort. Archived native comparisons also carry a time/version difference. This
does not establish subscription/API equivalence, real-agent resistance, or
independent human label validity.

## Gaps this would leave

**Luna native stability:** the frozen plan still has **800 unattempted repeated
Decisions classifications**: 100 groups × two pages × four conditions. These
need the same `gpt-6-luna` Decisions API configuration and fresh repeat evidence,
matched to its existing first outcomes. Current subscription documentation
establishes Responses access, not Decisions access. A Luna Responses or Codex
subscription run would be a newly named configuration and cannot fill this gap.
Defer native repeats until legitimate API allowance is available and a new
bounded execution is authorized. Keep original ties/errors in the denominator;
do not replace them with repeated answers. The archived repeat-subset baseline
has 798 valid classifications and two length-condition ties. A later 800-call
series measures temporal reproducibility against that archive. A new same-session
baseline-plus-repeat study would require **1,600 native API calls** in a separate
series. The 109 valid Luna Responses main
outputs likewise do not constitute the planned general comparator.

**A second task-bearing source:** PromptShield adds complete-request transfer
evidence; its released inputs have no separate authentic task field. Finishing
its missing model cells would not replicate the task-context intervention.
Before another large inference run, prepare one source with an original task,
the exact observed tool/page input, and defensible benign/attack labels. Check
historical exposure, task/template clusters, pairing and license; freeze labels
without using detector predictions. Independently review genuine benign
procedural instructions and task-related attacks. Human semantic review is still
missing; the partial Sol audit is an unblinded diagnostic.

The most concrete offline starting point is an **ASB cache feasibility check**,
before promising a sample size. First locate already-acquired task/tool records;
the confirmed canonical cache contains code and a license, not a prepared paired
corpus. A names-only scan located no provenance-backed task/tool-record cache;
an unidentified hash-named cache has not been ruled out. The three-case adapter
review therefore cannot start from verified cached records now. Stop this
feasibility step without acquisition or invented pairs. For later preparation,
first establish the pinned records, then inspect three prespecified task cases. The pinned
[inventory](../../results/source-discovery/agent-datasets.json) at revision
`544540ff0788998072f7df463056fd17e62cc9f4` lists 51 authored normal-task strings in
10 agent/scenario records, not a ready paired static dataset. The prior
[code audit](../study-v5/RESEARCH.md) found observation injection assembly but
could not reconstruct the original clean observation and exact alignment.
Require the released task/profile/tool schema, unchanged tool call, full original
clean observation, exact attacked observation, label basis, license and historical
exposure closure. Do not form arbitrary task-by-attack combinations or invent a
clean observation by deleting attack text. If cached evidence cannot establish
those fields, stop this adapter attempt and record the unresolved gap.

If faithful cases exist, independently review up to 20 pairs before defining a
larger sample. Even a later separately authorized ten-component Sol feasibility
pilot would be at most 80 calls, not confirmatory replication of the small v7
effects. ASB's tasks are benchmark-authored, not production user captures, and
its freshness remains unverified. Existing AIB, INFUSE, AgentDyn and InjecAgent
cases are historical exposure or replication material, not automatically fresh
data. An explicitly constructed source can be a separate diagnostic but must not
be called authentic released evidence. Count independent task families, not attack
variants. Freeze the attainable group count and a prospective precision plan
before evaluation. See the existing [source audit](../source-discovery/README.md)
and [source boundaries](../study-v6/SOURCES.md).

The focused next step is this route recovery and one general comparator, while
preparing the second task source offline. Broad inference and manuscript writing
remain stopped. No current evidence requires rerunning the completed native study.
