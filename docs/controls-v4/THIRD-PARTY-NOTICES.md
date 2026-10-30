# Source and component notices

The proposed TaskTracker subset deterministically reconstructs published QA inputs
from Microsoft [TaskTracker](https://github.com/microsoft/TaskTracker/tree/b4fabe25504dc1d3f7c6fdf5e50d4bb209a152b0)
(MIT), [SQuAD 2.0](https://rajpurkar.github.io/SQuAD-explorer/)
(CC BY-SA 4.0), and [AdvBench](https://github.com/llm-attacks/llm-attacks)
(MIT). MIT notices are retained in licenses/. SQuAD is by the Stanford authors
Rajpurkar and collaborators; source records retain the original Wikipedia article
title and passage. Individual original Wikipedia revision IDs are not supplied by
this reconstruction, and no exact original-page version is claimed.

The selected QA data and its adaptations retain [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Recorded transformations are the publisher's insertion/formatting, extraction of
candidate and original task, and this experiment's declared information controls.
This notice applies to source-containing artifacts, not a blanket relicensing of
unrelated harness code. TaskTracker's model outputs and GPT verifier scores are not
used as gold. CodeAlpaca NC data remains audit-only in ignored local storage.

The supplementary [agent-injection-bench](https://github.com/sentinelden/agent-injection-bench/tree/d75c8ad8d255d018b75258d22ea1c78a8c37428b)
fixtures are copyright 2026 Sentinel Den, MIT. They are authored synthetic scenarios,
not original records from the papers mentioned in their source fields. Candidate
and task text remain unchanged; excluded channels/context are recorded separately.

Reused development data retains the component licenses and attributions in
`docs/expanded-v2/dataset-review.md` and its original per-row provenance. No new
rights over those inputs are claimed. No restricted raw downloads or credentials
are included in Git.
