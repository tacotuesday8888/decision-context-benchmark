# Abstract

Does authentic task context improve prompt-injection detection beyond the effects
of additional instructions? We evaluated Jev, Laya, Nimble, GPT-6 Luna, GPT-6 Astra
and ProtectAI in seven configurations on 761 published task–content pairs,
representing 582 distinct texts and 138 task groups across nine source groups.
Paired comparisons measured classification errors and, where available, native
probability scores, with grouped uncertainty estimates. Empty-field, reminder and
scrambled-task controls covered 83 preselected pairs. We retained all 11,387
evaluation attempts, including seven transport failures and 13 abstentions.
Task context reduced missed attacks for several models on selected sources;
Astra's direct-harm misses fell from 36/129 to 8/129. However, its small control
subset showed no advantage over reminders or scrambled tasks, and other models
showed mixed or adverse effects. Shared templates, repeated texts and inherited
construction labels limit generalization. These findings motivate broader independent
task coverage, human-reviewed label semantics and better-powered controls; they
do not establish operational attack prevention.
