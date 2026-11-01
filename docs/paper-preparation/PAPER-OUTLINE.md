# Paper outline

## Question
Does providing the user’s task improve prompt-injection detection in decision models and general-purpose language models?

## Background
Briefly compare decision-model research, prompt-injection detection and existing task-aware defenses. Do not claim we invented task-aware detection.

## Methods
Explain the earlier 761 task–text combinations, the larger 3,000-pair study, and the 500-pair Sol subset separately. List model versions, interfaces and four input conditions. Define false alarms, missed attacks and their equal average. Explain grouping, missing answers and publisher labels.

## Results
Show the main task-versus-control effects and both kinds of error. Keep Jev’s increased missed attacks visible. Include the DTap counterexample; do not turn different model samples into a leaderboard.

## Discussion
Explain what changes with task information, why source and control choice matter, and what remains uncertain. The small synthetic agent test showed no protection benefit. Grouping reduces duplication without guaranteeing independence.

## Conclusion and references
State only what the tested configurations support. Cite the data sources and closest methods. Link code, figures and reproduction instructions. Write the abstract after the main text.

This is an outline, not a manuscript. The earlier page-budget draft remains a historical planning record.
