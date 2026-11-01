# What we learned from the overnight experiment

November 1, 2026. Collection is finished. The main numbers, external results, repeat checks and spending below were independently reconstructed from saved records. Corrected charts and frozen code/data hashes also passed review. Final private-branch delivery checks are still being completed; this note will be updated when those checks finish. No paper has been written or submitted.

## The question

Does telling a prompt-injection detector what the user is actually trying to do help it classify a suspicious page?

We showed the same pages with four kinds of context: the real task, an empty task field, a generic warning, and unrelated filler of similar length. This helps separate useful task information from simply adding more words.

## The main finding

**Task information helped Jev but hurt Luna Decisions on this dataset.** More context did not automatically make both models better.

The table shows how much the error rate changed when we supplied the real task, compared with each control. A percentage point means one additional correct or incorrect answer per 100 examples, approximately.

| Compared with | Jev: fewer errors with task | Luna Decisions: more errors with task |
| --- | ---: | ---: |
| Empty task field | 1.28 percentage points | 1.40 percentage points |
| Generic warning | 2.37 percentage points | 1.16 percentage points |
| Similar-length filler | 1.07 percentage points | 1.77 percentage points |

These six comparisons use the same 2,850 fully answered groups out of 3,000 planned groups. Each group contains a benign and an injected page. The preplanned tests account for making six comparisons; all six adjusted p-values are below 0.001. The effects are measurable but modest.

We also kept all 3,000 planned groups in a separate check: allow every unanswered or undecided classification to be either right or wrong. Even under those extremes, each effect keeps its direction in this particular tested dataset. Those ranges are **not confidence intervals** and do not establish how every future dataset will behave.

## How much data we actually used

- Main test: **6,000 distinct pages in 3,000 groups**, from BrowseSafe++. Two native decision models, four conditions: **48,000 requests**. Those requests are not 48,000 independent examples.
- External test: **4,000 texts** from PromptShield. Jev and ProtectAI each evaluated all 4,000.
- Local baseline on the main test: **1,000 pages**, a preselected subset of the 6,000 above.
- Consistency check: **800 repeated Jev requests**, drawn from 100 preselected main groups across four conditions. These are repeat measurements, not extra independent data.
- Development examples and the incomplete AI-assisted audit were kept separate from the main result.

The source datasets were not invented by us. They contain material constructed or rewritten by their publishers. We added controlled context conditions. The exact source versions, selection process and original labels are saved. Source labels are the reference standard here; they are not a guarantee that every ambiguous example is correctly labeled.

## The other findings

Jev changed its yes/no answer on **9 of 791 repeat pairs where both answers were usable**—about 1.14%. Nine of the 800 pairs lacked two usable binary answers, mostly because of ties. The original answers were never replaced by the repeats. The returned probabilities also changed slightly. This checks consistency over this repeat run, not long-term stability.

On PromptShield, Jev's balanced error was **25.63%**, compared with **48.35%** for this ProtectAI baseline. Balanced error gives benign and attack examples equal weight. Jev still missed **1,013 of 1,990 attacks with usable answers**; ten more attack cases were ties. ProtectAI missed **1,921 of 2,000 attacks**. Being better than this baseline does not make Jev reliable protection.

ProtectAI here means the pinned, published DeBERTa detector running locally, with the planned full-text windowing rule. It is a particular older model and configuration—not a claim about every product or newer model from that organization. Running those same weights through an API would not itself make them stronger.

## What did not finish

OpenAI API credits ran out after the full native main test. The API Responses comparison has only **109 usable main answers out of 4,000 planned**, plus two failed calls; it cannot support the intended broad comparison. Its external tests and repeat tests were not run. Luna Decisions' external and repeat tests were also deferred.

Sol's subscription route failed during the earlier audit. Its confirmation comparisons were not run. We did not replace them with another route, retry failed first attempts, buy credits, or recharge. The audit contains 70 completed AI reviews of 100 planned pairs and is not an independent human gold-label study.

Missing comparisons remain visible in the reports. The overnight run is therefore **a completed bounded execution with an incomplete original model panel**.

## What it cost

| New overnight usage | Recorded amount |
| --- | ---: |
| OpenAI | $29.69410125 |
| TypeSafe / Jev | $5.951424192 |
| Total with returned usage | **$35.645525442** |
| Additional conservative holds for five OpenAI calls without usage | **$1.9952816** |
| Total including those holds | **$37.640807042** |

These are usage-based estimates, not provider invoices. They exclude earlier studies. Including the preserved historical accounting gives **$46.495951176**, including historical and new unknown-cost holds. No subscription purchase or recharge occurred. The free Codex reset was not needed; it would not refill API credits.

The complete accounting log has 60,186 dispatches and 60,186 recorded outcomes, including development and earlier failed attempts. Its hash chain verifies. There are no duplicate dispatches, open reservations or calls left in flight.

## Is this enough for a good paper?

It is enough for a substantive, narrowly framed result: **task context has model-dependent effects on static prompt-injection classification**. The paired controls, fixed data selection, shared comparison groups, repeat measurements and explicit missing outcomes make the evidence more credible than a collection of favorable examples.

It does not yet support a broad claim that one model family is safer, that a decision API is inherently better, or that agents are protected from real attacks. We did not measure downstream agent actions, training-data exposure, or a general speed advantage. Related papers already study context and decision manipulation, so novelty must be argued around this specific controlled comparison, not “context matters” alone.

More random examples are not the immediate need. A useful next study would complete an independent general-model comparison, repeat Luna's results, and test the same task-context intervention on another dataset that genuinely contains user tasks. Targeted independent review of ambiguous labels would strengthen the label claims. That is future work, not something silently added after seeing these results.

## Where the work is

- Executor and full results: `/Users/langqi/Developer/Projects/Decision Context Benchmark Plan/results/study-v7-execution/`
- Frozen protocol, execution history and amendments: `Decision Context Benchmark Plan/docs/study-v7/`
- Independent checks and literature review: this `docs/overnight-research/` folder.
- Primary result checks: `independent-primary-results.json` and `primary-results-crosscheck.json`.
- External/repeat checks: `external-repeat-results-crosscheck.json`.
- Final spending check: `final-accounting-independent.json`.
- Literature: `decision-model-papers.md` and `detector-papers.md`; 16 focused paper reviews, with reading depth and limitations recorded.
- Private draft work: [executor PR 14](https://github.com/tacotuesday8888/decision-context-benchmark/pull/14) and [independent review PR 13](https://github.com/tacotuesday8888/decision-context-benchmark/pull/13). Neither is public publication or a merged release.

The original pilot and older study records remain preserved. The next step after verification is a decision about a carefully scoped follow-up or a narrowly framed write-up, not more spending by default.
