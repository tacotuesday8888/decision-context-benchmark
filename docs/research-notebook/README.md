# Experiment notes — what we tried and what happened

Reconstructed on November 1, 2026 from saved protocols, completion audits, results and recent experiment-chat handoffs. This is a retrospective research record, not a contemporaneous lab diary, raw dataset or manuscript. It summarizes verified records; it does not independently repeat every historical audit. Evidence snapshot: commit `5f4e667db22a4dc404d79597a88657d3a9d272f6`.

Editable discussion copy: [Google Docs notebook](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit). This Git version is the source-linked snapshot; later Google edits are not automatically synchronized.

## Working notes, not a finished paper

The project is still being interpreted. The useful story is what was tried, what changed, what surprised us and what needs checking. These notes are meant to make that discussion easier, not to make the project sound more finished than it is.

A few things worth talking through:

- Giving a detector more information did not reliably make it better.
- Jev raised fewer false alarms but missed more attacks. Which mistake matters more in a real application?
- A longer prompt sometimes explained an apparent improvement. That is why the extra controls mattered.
- The small agent pilot did not show a protection benefit. It also exposed a scoring rule that was too picky about answer formatting.
- More model calls do not fix unclear labels. Some examples still need a person to read them carefully.

Space for personal notes (not filled in by the assistant): What did I expect? What surprised me? What do I still not understand? What would I change next time?

## The question

Does knowing the legitimate user's task help a model distinguish useful content from prompt injection? A detector can make two different mistakes: flag harmless content (a false alarm), or let an attack pass (a missed attack). An improved average score can conceal more missed attacks.

This project evaluates specified model configurations against released source labels. It does not establish universal model rankings, independently verified semantic truth for every label, or dependable protection for a working agent.

## Counting examples correctly

A **task–content pair** is one task associated with one candidate piece of content. This is a descriptive unit defined for this study, not a newly invented scientific method. A **clean/attack pair** groups two content examples under a task. A **request** is one model call: repeating an example across models or prompts does not add independent examples.

| Stage | Planned or recorded data | What the number means |
| --- | --- | --- |
| Expanded v2 | 402 evaluation candidates; 60 development candidates | Earlier evaluation, separate from the 761 stage |
| Context extension v3 | 761 task–content pairs; 582 distinct texts; 138 tasks | Completed stage described in the activity statement |
| Controls v4 | 425 confirmation texts; 221 tasks; 44 primary clusters | 408 QA rows and 17 supplemental fixtures; not 425 independent task families |
| Larger v7 study | 3,000 clean/attack groups; 6,000 pages | Jev and Luna Decisions each evaluated all pages under four conditions; 2,850 groups complete across both models |
| Sol follow-up | 500 groups from v7; 1,000 pages | A subset, not 500 new groups; 498 Sol-complete and 471 shared-complete groups |
| PromptShield check | 4,000 texts | Separate detection benchmark; not an authentic-task intervention |
| Second-source diagnostic | 66 groups; 132 observations | Released simulated-service data; 64 legal and two CRM groups; 62 shared-complete groups |
| Action pilot | 12 constructed tasks | Authored one-step fake-world cases, not production incidents |

Do not sum this table into a unique-example total. Units differ, some sets overlap, and a project-wide deduplicated union has not been established. Confirmation counts, development records, repeats and AI audits must remain separate. Prepared v5/v6 inventories are not automatically completed evaluations.

## Research history and why the design changed

The order below is reconstructed from versioned stages. It is not a claim that all work occurred on the notebook's creation date.

1. **Pilot and expanded v2:** established routes, data preparation and source-specific detection comparisons. Expanded v2 completed 5,274 logical cells. An older 11-page draft exists for that earlier study; it is not the planned new five-page paper. [Pilot record](../../results/pilot/report.md); [v2 completion audit](../expanded-execution/COMPLETION-AUDIT.md).
2. **The 761-pair extension:** evaluated authentic source-backed task/content associations across multiple configurations. The final record retains 11,387 confirmation attempts, including 13 ties and seven transport failures. Mixed results did not establish a general benefit specific to meaningful task information. [v3 completion audit](../extension-v3/COMPLETION-STATUS.md).
3. **Controls v4:** strengthened comparisons with other prompt changes. Astra's QA advantage over empty formatting was matched by a reminder and scrambled words. That made it important to separate task meaning from generic prompting effects. [v4 completion audit](../controls-v4/COMPLETION-STATUS.md).
4. **Source expansion and v5/v6 preparation/execution records:** investigated additional sources, reviewed grouping and label concerns, and built bounded execution tooling. Preparation documents describe proposals as of their own dates; they must not be read as final current status. [v5 handoff](../study-v5/HANDOFF.md); [v6 preparation handoff](../study-v6/HANDOFF.md); [review-resolution handoff](../study-v6-review-resolution/HANDOFF.md). These intervening records remain distinct; this notebook does not claim a complete new audit of every v6 outcome.
5. **Larger v7 evaluation:** tested task context against empty-task formatting, a generic reminder and character-matched filler. Jev and Luna each completed 24,000 main first attempts. Other planned routes were partly completed or deferred after access/credit limits; the saved coverage table reports them. [v7 results and coverage](../../results/study-v7-execution/README.md).
6. **Subscription follow-up, completed November 1:** completed the separately frozen Sol comparison, repeats, blind AI audit, second-source diagnostic and small pilot. All 5,638 scheduled follow-up requests are terminal: 5,629 parsed status-ok outputs, three service failures and six ties. These are calls, not unique examples. [Core record](../../results/subscription-followup-execution/README.md); [extension record](../../results/subscription-followup-extensions-execution/README.md).

The 761-pair stage is meaningful original project work. Later experiments test and qualify its interpretation. The activity description does not require selecting weaker evidence or presenting later tests as unimportant.

## What the results support

| Finding | Evidence and interpretation |
| --- | --- |
| Jev's average improved with a security tradeoff | On 2,850 shared main groups, false alarms fell from 12.88% to 6.63%, while missed attacks rose from 8.11% to 11.79%, versus empty-task formatting. Balanced error weights these two rates equally. |
| Task information did not help every configuration | Luna main error increased. On 498 complete Sol groups, task BER was 11.8474% versus format BER 10.7430%. Sol task error increased by 1.10–1.31 percentage points relative to the three controls. |
| The source and control matter | On 62 shared second-source groups, Sol improved against format/reminder but its difference against length control was inconclusive. This small, predominantly legal source stays separate from the main dataset. |
| Short-run predictions were usually consistent | Sol changed 3/397 usable repeated predictions; Jev changed 9/791. Luna's identical native subscription repeat route was not verified. Consistency is not correctness. |
| The pilot did not prove protection | Ungated attacker success was already 0/12. Blocking attacked observations removed useful facts. The frozen 11/12 extraction score also rejected one substantively correct answer because of a unit-format mismatch. Scores and raw records were preserved. |

Numerical sources: [v7](../../results/study-v7-execution/README.md), [Sol](../../results/subscription-followup-execution/README.md), [second source and pilot](../../results/subscription-followup-extensions-execution/README.md). Their tables retain comparison-specific denominators and uncertainty. No cross-source pooled winner is claimed. Nonconcurrent model comparisons differ in model, route and collection time, so they do not isolate architecture or size.

## What has been checked, and what remains

Saved independent computational reviews reconstructed raw outcomes, cohort counts, effects and uncertainty calculations. Frozen first attempts and failures were retained. Compact outcomes and analysis code support the documented offline replays. Full transports and restricted source text remain in ignored local storage, connected through hashes. A hash alone does not make unavailable data publicly reproducible.

The blind AI audit agreed with 198/200 publisher page labels but flagged ambiguity in 23 pairs. This is AI review, not independent human ground truth. The most useful next validation is a blinded human check of ambiguous cases, decision changes and a small random sample. Record it separately without silently changing frozen primary labels or excluding unfavorable cases.

Before a manuscript: finalize the claim-to-evidence list, select figures showing both errors, document source-label and independence limitations, check reproduction instructions, and obtain the requested skeptical Astra High review. That review has not been started for this notebook. No new inference is needed merely to create these notes. A claim about stability across every model would need the missing Luna repeat evidence. An agent-protection claim would require a separate stronger study.

## Contribution record and teacher discussion

This notebook was assembled by an AI assistant from project records at the owner's request. AI agents performed substantial coding, execution management, analysis and documentation. The owner directed the project and made scope/access decisions in the chats. The owner's further hands-on work and the teacher's contributions must be recorded by those people; they are not inferred here. No teacher approval or human label review is claimed.

Owner notes — to be completed: What question did I choose? Which design decisions did I make? Which code/results have I personally inspected? What explanations can I give without assistance?

Teacher notes — to be completed: What was reviewed? Which interpretations or labels need correction? What guidance was provided, and when?

Discussion prompts: Why can fewer false alarms accompany more missed attacks? Why use the same examples across prompt conditions? Why does a length control matter? What do source labels fail to guarantee? Why did the pilot fail to demonstrate a security benefit?

## Next working record

- Human label review: not yet recorded here.
- Claims/figures critical review: pending; Astra not launched.
- New five-page manuscript: not drafted in this phase.
- Project-wide unique-example union: not claimed.
- Publication or repository merge: not performed by this documentation task.

For future entries, record date, question, action, evidence path/commit, result, limitation and next decision. Keep new observations distinct from retrospective summaries. A proposed five-page main text may use separate references and supporting materials; page count is not a measure of scientific quality.
