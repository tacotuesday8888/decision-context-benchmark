# Experiment notes

Weekend research update · November 1, 2026

The study was expanded using existing models; no models were enlarged or retrained. These notes summarize the project to date, not a claim that every experiment was first completed this weekend.

## Question

Does giving a prompt-injection detector the user's actual task help it make fewer mistakes?

## What was tested

- Earlier study: 761 task–content combinations from AgentDojo, AgentDyn and InjecAgent, covering 582 distinct texts and 138 tasks. Tested Jev 1.14.0, GPT-6 Luna through two interfaces, GPT-6 Astra, Nimble Q4_K_M, Laya multilingual and ProtectAI v2. ProtectAI judged content without a task; it was a reference detector, not a task-context comparison.

- Larger study: 3,000 normal/attacked webpage pairs from BrowseSafe++ (6,000 page versions), tested with Jev and GPT-6 Luna through its Decisions interface. The main comparison uses 2,850 pairs with complete answers across both models and all four conditions.

- GPT-6.1 Sol follow-up: 500 pairs selected from that larger study; 498 had complete answers for the main Sol comparison. These are not 500 additional independent pairs.

- Other checks: 4,000 PromptShield texts tested with Jev and ProtectAI v2; 66 DTap pairs tested with Jev and GPT-6.1 Sol; and 12 authored simulated-action tasks. Not every model was tested on every dataset.

A task–content pair means one task linked to one piece of content. A clean/attack pair contains two examples. These counts overlap and use different units, so they should not be added together.

The main study kept each page unchanged and compared four prompts: an empty task field, the published user task, a generic warning, and filler matched by character count. These controls help test alternative explanations, but do not perfectly isolate task meaning.

The source supplies the normal/attack labels. Some tasks and labels are unclear; they have not all been independently checked by humans. BrowseSafe++ uses rewritten pages from its released training partition; our selected evaluation pages are not its official test set. The small action test is explicitly synthetic.

## What happened

- Jev: compared with an empty task field, false alarms fell from 12.9% to 6.6%, but missed attacks rose from 8.1% to 11.8%, using publisher labels. Averaging those two error rates equally gives 10.49% before and 9.21% after. This does not prove that overall real-world safety improved.

- GPT-6.1 Sol and GPT-6 Luna: adding the task increased the average of the two error rates on the main dataset. Sol's increase was about 1.1–1.3 percentage points versus the three controls. Sol used a smaller subset, so this is not a direct model ranking.

- DTap: GPT-6.1 Sol improved against the empty task field and generic warning, but its advantage over character-matched filler was unclear. Only 62 pairs had complete answers across both models; 64 of the 66 planned pairs were legal-domain examples. This limits any claim that Sol always gets worse with task information.

- Agent pilot: no protection benefit demonstrated. The ungated actor already resisted all 12 attacks. Blocking information also removed facts needed for the task.

- Scoring issue: one correct answer containing “12 units” failed a rule expecting “12”. The original score is preserved, with the issue documented.

Takeaway: task context changes decisions, but it does not consistently improve detection. Both false alarms and missed attacks matter.

## Still to check

- Start with the four short examples: https://docs.google.com/document/d/1h5RO4VKXj-eB-dk3-C2v0YRtCl9n_DrriGXa66m7lbk/edit

- These are simplified excerpts, not a full-dataset check. Please answer independently; “Not sure” is useful. Claude separately reviewed 32 pairs as an AI review, not human validation.

- Figures now show both kinds of error and the task-versus-control comparisons. Check whether the explanations are understandable.

- Keep conclusions tied to these datasets and fixed model settings. Related pages can remain similar even after grouping; model calls are not additional independent examples.

- GPT-6.1 Sol on Medium has reviewed the prepared figures and claims. It found no numerical mismatch; the wording issues it identified have been corrected. An AI review is not a substitute for a teacher's or researcher's judgment. The five-page outline is ready; the paper has not been written.

## Related work and how this project differs

To Jev or Not? compares decision models on hate-speech classification and changes the definitions supplied to them. Our question concerns user tasks and prompt injection instead.

https://arxiv.org/html/2610.03324v1

CAD trains a filter to detect malicious sentences using the user's query and surrounding text. Our main study tests existing whole-page classifiers without retraining them.

https://arxiv.org/html/2608.05430

Task Shield checks whether instructions and tool calls serve the user's goal while an agent works. Our main results measure saved-text judgments, not live-agent protection.

https://aclanthology.org/2025.acl-long.1435/

These are related methods, not additional datasets we ran. The dataset sources actually used are named above. Task-aware detection already exists; we are not claiming to have invented it.

## Meeting goals

Check the four examples, discuss whether the conclusions are fair, choose the clearest figures, and agree on a five-page paper structure. The evidence supports starting a careful comparison paper; it does not establish a universal defense.

## Records

761-pair study: https://github.com/tacotuesday8888/decision-context-benchmark/blob/5f4e667db22a4dc404d79597a88657d3a9d272f6/docs/extension-v3/COMPLETION-STATUS.md · Main results: https://github.com/tacotuesday8888/decision-context-benchmark/blob/5f4e667db22a4dc404d79597a88657d3a9d272f6/results/study-v7-execution/README.md · Sol results: https://github.com/tacotuesday8888/decision-context-benchmark/blob/5f4e667db22a4dc404d79597a88657d3a9d272f6/results/subscription-followup-execution/README.md · Second source and pilot: https://github.com/tacotuesday8888/decision-context-benchmark/blob/5f4e667db22a4dc404d79597a88657d3a9d272f6/results/subscription-followup-extensions-execution/README.md

Editable notes: https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit
