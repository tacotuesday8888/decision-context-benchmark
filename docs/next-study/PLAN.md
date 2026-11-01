# Plan for the expanded experiment

Prepared November 1, 2026. Status: **preparation authorized; experimental inference paused**.
This is a new study proposal, v7. It does not alter or complete the frozen v6 experiment.

## The question

Does showing a model the user's real task help it spot malicious instructions in a webpage?
Does that help more than simply telling the model to be careful?

We will test this by showing the same pages with different information. We will count
missed attacks and useful pages incorrectly flagged. We are testing a detector, not
proving that an entire browsing assistant is safe.

## Decisions made

| Part | Decision |
|---|---|
| Main data | BrowseSafe++, 3,000 fresh groups, one clean/attacked page pair per group: 6,000 pages |
| Separate check | PromptShield, 4,000 unique test requests: 2,000 per original label |
| Main models | Jev 1.14.0 and GPT-6 Luna Decisions, both through their native APIs |
| General comparisons | GPT-6 Luna and GPT-6.1 Sol through the OpenAI Responses API |
| Specialist comparison | The existing local ProtectAI DeBERTa v2 model |
| General-model sample | The same 500 main groups for both models; the same 1,000 external requests |
| New local models | None. No Llama. Laya and Nimble stay in historical records, outside this new bounded run |
| Expected test cost | Approximately $95–$120 additional, including the limited example audit |
| Proposed new spending limits | $350 OpenAI for tests/audit, $25 OpenAI for optional writing/coding assistance, $20 TypeSafe: $395 total ceiling |
| Time target | 20 active project hours, with model runs and writing overlapping |
| Deliverable | An approximately five-page paper, checked charts, code, and an honest account of limitations |

These are targets, not newly acquired or completed data. The cost limit is a proposal,
not permission to spend it. The current $15 OpenAI / $20 TypeSafe cumulative limits
remain in force until a new bounded run instruction is given.

## What is already useful

The project has working source adapters, request logging, spending controls, saved
model answers, and analysis/reporting code. The frozen main v6 run covers 988 pages
in 487 groups; Jev and Luna Decisions completed their requests. Other comparisons
and final analysis remain unfinished. We preserve this experiment as an earlier,
separate study. We do not silently combine it with the new one or call it complete.

## What changes now

1. **More fresh examples.** Exclude every BrowseSafe++ group previously selected by
   this project, including examples later rejected. There are 10,177 remaining
   English task/reference groups in the metadata before further similarity checks.
   A 3,000-group main test plus 200 development groups is plausible; preparation
   must verify the final count.
2. **Two datasets, two clear jobs.** BrowseSafe++ tests the benefit of task information.
   PromptShield checks detection on another collection. PromptShield has no separate
   trustworthy task field, so we will not invent one.
3. **Use published labels.** Keep original dataset labels as the main reference.
   Check a fixed 100-group sample for task fidelity, visible attacks, and ambiguity.
   This is a documented AI-assisted check, not human ground truth or another
   requirement to relabel everything. Its model calls remain paused too.
4. **Keep the comparisons manageable.** Five configurations represent four named
   models: Luna appears through two interfaces. The larger general model is Sol,
   not the much more expensive Astra. This supports conclusions about the systems
   tested, not every decision model in existence.
5. **Keep the test fair.** Give each compared system the same relevant examples,
   freeze prompts and settings before testing, and keep failures in the record.

## The 20-hour schedule

The clock is a project-work target, not a promise about provider availability.
This planning/handoff work occupies the first stage; record its actual time rather
than resetting the clock when the next chat starts.

| Project hours | Work | Required result |
|---|---|---|
| 0–2 | Finish plan, source/model choices, cost calculations and independent critique | This plan and its checked assumptions |
| 2–4 | Acquire text, remove overlaps, form groups, implement paid API routes and run offline checks | Exact data/request manifests and offline-ready runner |
| 4–12 | After explicit run authorization only: operational checks, bounded audit, lock setup and run tests; draft methods while calls run | Saved first responses and coverage/cost records |
| 12–16 | Independently verify calculations, make charts, inspect errors | Checked results with uncertainty and limitations |
| 16–20 | Write the paper, verify every number, inspect the PDF and deliver privately | Verified paper and reproducible artifacts, or a clearly marked incomplete report |

Historical native throughput suggests about 6.1 hours for the new native calls.
Paid Sol throughput and current rate limits have not been measured. Run providers
concurrently under one spending controller; do not assume agent concurrency creates
more API allowance. If preparation exceeds its slot, report the cause and revised
finish estimate rather than claiming the original deadline still holds.

At the declared collection cutoff, finish already reserved groups and stop admitting
new ones. Do not inspect accuracy to decide whether to continue. A deadline cannot
turn incomplete or unverified results into a finished empirical paper.

## What we do not need for this paper

We do not need training a new model, a leaderboard of dozens of models, a new agent
environment, screenshots, every available dataset, or repeated changes to the
prompts after seeing results. We do need fresh data, useful controls, transparent
labels, correct arithmetic, and conclusions that match the evidence.

## Ready to prepare; not ready to spend

The next chat can download the approved text-only training data, prepare the fixed
samples, implement the new routes, write tests, calculate exact token budgets, and
prepare the paper outline. It must not call classification/review models, resume
v6, buy anything, or submit/publish the paper.

Before a paid run, the exact sample, model access, rate limits, prices, total
reservations, and statistical checks must be verified. A model appearing in an API
catalogue is not proof of successful inference or available credit. A future
subscription can help with code and writing; it must not silently replace an API
configuration partway through the experiment.

Technical instructions: [PROTOCOL.md](PROTOCOL.md). Cost assumptions and arithmetic:
[forecast.json](../../results/next-study/forecast.json). Review findings and sources:
[REVIEW.md](REVIEW.md). Preparation-chat instructions: [HANDOFF.md](HANDOFF.md).
