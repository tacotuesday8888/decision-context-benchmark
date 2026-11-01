# Experiment notes

Project update · November 1, 2026

## The question

Does telling an AI what the user wants help it spot prompt injection—text that tries to make it ignore the user’s request? We compare decision models such as Jev with general-purpose language models.

## What we tested

Earlier study: 761 task–text combinations from AgentDojo, AgentDyn and InjecAgent. These contain 582 different texts and 138 tasks.

Larger study: 3,000 normal/attacked webpage pairs from BrowseSafe++—6,000 page versions—tested with Jev and GPT-6 Luna. Their main comparison uses 2,850 pairs with complete answers.

GPT-6.1 Sol: tested on 500 pairs selected from the larger study; 498 had complete answers. These are not additional independent data.

Other checks: 4,000 PromptShield texts, 66 DTap pairs (62 complete), and 12 small, invented agent tasks. Not every model ran on every dataset.

## Models and method

Across the studies: Jev, GPT-6 Luna, GPT-6 Astra, GPT-6.1 Sol, Nimble, Laya, and ProtectAI v2. Luna used two interfaces; ProtectAI v2 is a specific detector, not a general-purpose assistant.

In the larger study, we kept each page unchanged and compared four inputs: no task, the actual user task, a general warning, and filler of the same character length. We tested existing models; we did not train or enlarge them.

## What we found

Jev flagged fewer normal-labeled pages: 12.9% fell to 6.6%. But it missed more attack-labeled pages: 8.1% rose to 11.8%. These figures compare no task with the actual task.

GPT-6 Luna and GPT-6.1 Sol made more errors on average in the main comparison. On the smaller DTap set, Sol improved against some controls, but its advantage over filler was unclear.

The 12-task agent test did not show a protection benefit: no attacks succeeded even without the extra filter.

Main finding: task information changes mistakes, but does not reliably improve detection. We cannot name one model type as the universal winner.

## What the results cover

We use the dataset publishers’ labels, which can be unclear. BrowseSafe++ contains rewritten pages; our sample comes from its released training collection, not its official test set. The small agent test is synthetic.

These studies use different units and overlapping samples, so their counts should not be added. Related examples may still be similar. The results do not prove that working agents are safer everywhere.

## Related work

To Jev or Not? compares decision models for hate-speech detection. CAD trains a context-aware text filter. Task Shield checks whether an agent’s actions serve the user’s goal. Our main study compares existing detectors with and without task information; it does not invent task-aware detection.

## Next steps

Review the four short examples with my teacher, discuss the findings and charts, and agree on the five-page paper structure. The results and outline are ready for discussion; the current five-page paper is not written.

Research records: private GitHub repository.
