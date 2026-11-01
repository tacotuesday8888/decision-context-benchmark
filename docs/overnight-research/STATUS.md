# Experiment status — November 1, 08:11 UTC

**The main experiment has started, but it is not finished.** We cannot yet say whether task context improves detection. We are checking service failures and costs while the run proceeds; we are not changing the experiment based on accuracy.

## What we are testing

Does telling a model the user's real task help it identify prompt injection? We compare the same page with the real task, an empty task field, a generic warning, and length-matched filler. This tests classification, not whether an autonomous agent resists an attack.

## Data and models

The main test contains 3,000 held-out BrowseSafe++ groups, each with a benign page and an attack page: 6,000 pages. A separate PromptShield test contains 4,000 requests. Development examples are separate. Duplicate and historical-exposure checks are saved, but they cannot prove that a model never saw these public sources during training.

The core models are Jev, Luna Decisions, Luna Responses, and the published ProtectAI model running locally. Jev and Luna Decisions use their native decision interfaces. ProtectAI is a reference detector; local hosting does not make its published weights smaller.

Sol's subscription interface produced 499 valid development responses. It then suffered repeated service failures across development and the audit. We preserved those failures and deferred Sol after the documented recovery limit. We did not switch to paid Sol.

## What has actually run

At this snapshot, 3,209 main-test first responses were saved across Jev and Luna Decisions: 3,203 valid classifications, four Jev ties, and two Luna service/rate-limit errors. These are model responses, not 3,209 independent examples. More records may exist after this timestamp.

The AI audit completed 70 of 100 planned reviews, with one failed call and 29 never sent. An independent quotation check found 390 exact source matches and one nonliteral span. This is an incomplete, unblinded AI review, not independent human validation. It does not replace the original dataset labels or filter difficult examples.

## Money

The new run's recorded usage is $2.68956375 OpenAI plus $0.481445454 Jev, approximately **$3.17**. Another **$1.05** remains reserved for two requests with unknown usage. These figures exclude older studies and are usage accounting, not a provider invoice or account balance.

Current authorized limits are $350 additional OpenAI experiment usage and $20 additional Jev usage. Expensive Sol API calls, paid coding assistance, purchases, and automatic recharge are disabled. The limits are ceilings, not spending targets.

## Current issue and what happens next

Luna reached its token-per-minute limit. The worker added and tested conservative pacing shared across both Luna interfaces. The run resumed, preserving both failed first attempts and their cost holds and sending only requests never sent. Prompts, data, models, statistical comparisons, and spending limits stay unchanged.

Remaining work is to finish the core calls and planned repeats; reconcile all failures, missing cases, and spending; compute the frozen comparisons and uncertainty intervals; independently verify the numbers and charts; and save a final plain-language handoff. No manuscript or LaTeX paper is being written.

New groups stop being admitted at **14:00 UTC / 9:00 AM New York**. The authorized work window ends at **16:06 UTC / 11:06 AM New York**. Completion before then depends on provider availability and throughput; unfinished cases will be reported rather than concealed.

## Where the work lives

- Execution: `/Users/langqi/Developer/Projects/Decision Context Benchmark Plan`
- Independent research and checks: `/Users/langqi/Developer/Projects/Decision Context Benchmark Research`
- Earlier studies, preserved: `/Users/langqi/Developer/Projects/Decision Context Benchmark`
- Detailed coordinator evidence: `docs/overnight-research/CONTROL.md`
- Private execution review: https://github.com/tacotuesday8888/decision-context-benchmark/pull/14
- Private research review: https://github.com/tacotuesday8888/decision-context-benchmark/pull/13

Raw examples, responses, and credentials are not included in these status notes. The repository remains private.

Update at 08:19 UTC: the paced run is active. The worker reports 3,493 of 48,000 planned native confirmation responses saved, with no new stop. Root independently checked the first 138 pacing events: maximum observed rolling weight 1,497,820, below the 1,500,000 soft limit. The money and detailed counts above remain the explicitly timestamped earlier snapshot.

Update at 08:29 UTC: the worker last reported 6,260 of 48,000 native confirmation records and remains active. Independent spending reconciliation now shows approximately **$5.49** in new recorded usage ($4.63367705 OpenAI and $0.855393042 Jev), plus the preserved $1.05 unknown-usage hold. No duplicate requests were found among 8,706 dispatches across development, audit, and confirmation. These are interim totals, not final bills or accuracy results.
