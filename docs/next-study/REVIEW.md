# Evidence and design review

November 1, 2026. Read-only research and planning, not independent replication of
the cited papers. No v6 confirmation predictions or accuracy were inspected to make
these selections. No model inference ran during this planning audit.

## Assessment of the existing architecture

**Keep:** immutable source/request hashes, separate development and confirmation,
whole-group scheduling, original raw responses, append-only spending reservations,
held unknown charges, explicit unsupported/failure states, and independent result
recalculation. These are useful safeguards, not reasons to restart the project.

**Change in v7 only:** reduce six source constructs to two clearly separate endpoints;
use original source labels rather than requiring all-row AI agreement; enlarge the
fresh main cohort; use paid general-model API routes with explicit settings; use a
simpler paired group-mean analysis; limit expensive/local model breadth; and write
one readable plan. Existing v6 schemas/freezes are not modified to accommodate v7.

**Do not overclaim:** neither the previous AI review nor the new audit establishes
human ground truth. A successful native detector result does not establish real
agent security. Four model IDs do not represent the whole model class. Low API cost
is not evidence of inadequate testing, and a high call count is not a large task set.

## Independent agent review and resolutions

Three subordinate agents checked data, cost/routes, and scientific design. They are
AI assistants with shared project context, not human peer reviewers or completely
independent replications. No predictions were supplied to select the design.

| Finding | Resolution in the proposal |
|---|---|
| Source labels were being treated as requiring wholesale re-annotation | Source-label agreement is primary;100-group audit is diagnostic and explicitly unblinded |
| Proposed300-group audit had unbudgeted inference/time | Reduced to100pair-review calls;forecast includes them and states limited precision |
| PromptShield is a complete request, not an external webpage | Separate frozen full-request question;no invented task or claim of task-effect replication |
| Sign randomization is not automatically valid for any zero-mean difference | Paired group-mean t tests with Holm6;whole-group intervals;actual null/power simulation still required |
| Unsupported inputs could silently shrink comparison denominators | Shared complete-pair native cohort plus full planned-group bounds and contrast-specific sensitivity |
| Deduplicating repeats could replay answers instead of measure stability | Fresh replicate namespace, identical payload bytes,new transport IDs/timestamps |
| Changing API/subscription partway could change the treatment | One fixed route per experimental configuration;subscription only for separate code/writing work |
| A20-hour promise could incentivize selective stopping or unchecked prose | Outcome-blind time/cost admission cutoff and explicitly incomplete delivery if checks cannot finish |
| Astra costs much more than Luna | Sol API selected as the stronger general comparator before evaluating new outcomes |
| API catalogue access is not inference access or credit | Read-only catalogue200 verified;paid inference/credit/rate-limit checks remain pending |
| Per-label external sampling could reuse a mixed-label near-duplicate group | Allocate components globally and enforce a shared used-component set before filling quotas |

Final read-only review reproduced the saved forecast exactly and checked70,500paid
attempts,5,200local records,$95.06–$118.04forecast,$343.48stress scenario and6.129hour
native runtime extrapolation. No remaining material planning contradiction was
identified. This is readiness for offline preparation,not for experimental execution.

## What similar studies teach us

| Primary source | Evidence checked | Practical decision |
|---|---|---|
| [To Jev or Not?](https://arxiv.org/html/2610.03324v1) |12,975testtexts across4sets;paired definition comparisons | Compare conditions on the same examples;do not assume adding context must help |
| [System One security decisions](https://arxiv.org/html/2609.33401v1) |Separate calibration/selection/confirmation/test;2,200allocatedtestinputs across3datasets | Keep thresholds fixed and report coverage, source-specific errors and uncertainty |
| [Decision Hijacking](https://arxiv.org/html/2609.28613v1) |510cases=17contexts x30goals;54,060maincalls | Keep source examples, independent groups and repeated calls separate |
| [JevOut](https://arxiv.org/html/2609.30243v1) |700heldoutsourceitems;508initiallycorrectJevitems in attack analysis | Disclose selected populations;never import model-success selection into our main test |
| [Type-Safe Is Not Error-Free](https://arxiv.org/html/2609.26758v1) |1,200workflowdecisions;neutral controls and test-retest calls | Freeze answer meanings and separate repeat instability from intervention effects |
| [Nudge the Judge](https://arxiv.org/html/2610.18612v1) |2,273cases across228applications | Distinguish detector decisions from demonstrated downstream consequences |
| [Broad Jev benchmark](https://arxiv.org/html/2609.37647v1) |346,009requests across37datasets for under$10Jev | Spending is not a quality metric;our narrower question does not require matching its row total |
| [Typed-decision evidence audit](https://arxiv.org/html/2609.32160v1) |28earlypapers;repeated reporting/calibration/comparison weaknesses | Borrow sound methods,not merely the average sample size or an impressive headline |
| [BrowseSafe++](https://arxiv.org/html/2610.17457v1) |Paired pages and task context;29,500labeledtrainingpairs | Main source;preserve rewritten provenance and avoid a detector trained on those pairs |
| [PromptShield](https://arxiv.org/html/2501.15145v2) |Roughly24k evaluation examples;paper acknowledges evaluation-set threshold selection | External dataset with frozen thresholds;do not reproduce that threshold-selection weakness |

The six focused studies above with base-case totals510,700,1200,2200,2273,12975 have
arithmetic mean3,309.7 and median1,700. This is a convenience selection with different
units, not a systematic field average or a sample-size justification. V7 uses an
explicit effect-size/variance sensitivity calculation instead.

## Source availability decisions

- [BrowseSafe++](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus):
  approved access already exists. Use pinned labeled training release only. Fresh
  remaining counts are metadata counts,not a completed3,200-group corpus.
- [PromptShield](https://huggingface.co/datasets/hendzh/PromptShield): pinned test
  downloaded into memory and SHA/count/schema verified;18.3MB;no payload committed.
  Original test23,516rows/23,359exactunique. Provisionalbalanced4000hashsample mean
 930.886characters,median587,max18,488. Forecast400tokens/request is an assumption
  including instructions,not an exact tokenizer measurement.
- WAInjectBench is not selected: current checked repository revision
  `ee55236860820b3639c9039a2aa367b2cb86d114` has no LICENSE and GitHub license=null.
  PromptShield offers clearer declared terms;this is not a claim WAInjectBench is unusable.
- AgentDyn is not selected: all60tasks have prior project exposure and integration
  would add a new agent-environment study. It remains a future direction.

## Pricing and access evidence

Official rates checked November1:
[OpenAI pricing](https://developers.openai.com/api/docs/pricing),
[Decisions](https://developers.openai.com/api/docs/guides/decisions#pricing-and-availability),
[Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching),
[TypeSafe](https://docs.typesafe.ai/models).

Per1Mtokens: Jevinput$0.042/outputfree;Lunainput$0.10/output$0.50;
nativeDecisionsoutputfree and12hwrite$0.25;Solinput$2/output$10.
Responsesexplicit-only caching without breakpoints avoids cache reads/writes;
its support must still pass authorized development before freezing the request.
No Batch discount is assumed for a20-hour target.

Authenticated `GET /v1/models` returned200 at2026-11-01T05:45:06.955753Z and listed
gpt-6-luna,gpt-6.1-sol,gpt-6-astra. Inferencecalls=0;modelinferenceverified=false.
No credentials are reproduced in this record. API and subscription billing are
separate;this plan does not alter the coordinator chat's login or billing.

## Skills applied

Installed skills read:experimental-design v1.5,statistical-power v1.3,
scientific-critical-thinking v1.5, from
`K-Dense-AI/scientific-agent-skills` revision
`5f2bc0341354fd5590aef76a533ada1e1e5b4e62`.
They guided the grouping, controls, power sensitivity and claims review;they are not
a certification of scientific quality. No third-party skill inference scripts ran.

Reference:Kassis,T.,Agarwal,V.,He,Y.,Patel,D.,and Brueckner,A.M.(2026).
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
Also [Lakens(2022),Sample Size Justification](https://doi.org/10.1525/collabra.33267).
Report materially used skill/software provenance in the eventual manuscript.
