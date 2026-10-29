# Research notes: inspected evidence, preliminary gap

This review is ongoing, not exhaustive. The working contribution is a paired
measurement of authentic trusted-task information in detection and native
probability quality, with text/format/reminder controls. Existing agent-security
benchmarks already examine context and helpful third-party instructions; do not
claim that context-aware detection itself is new. Dataset counts below come from
local pinned artifacts where stated, not model request counts.

- [InjecAgent, Findings ACL 2024](https://aclanthology.org/2024.findings-acl.624/):
  peer-reviewed agent attack evaluation. The inspected repository releases
  510 direct-harm plus 544 stealing cases; artifact audit identifies 17 user
  fixtures crossed with 30/32 attacker instructions. Enhanced cases reuse these
  combinations. MIT license verified. The user response templates contain an
  attacker placeholder, not a released clean substitute. Attack-only detection
  can measure misses, not false alarms or balanced accuracy.
- [AgentDojo, NeurIPS 2024 Datasets and Benchmarks](https://proceedings.neurips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf):
  peer-reviewed execution benchmark, 97 user tasks in four environments in the
  paper version. Current code has versioned task overrides; counting every class
  declaration inflates counts. MIT repository inspected. The official
  [results page](https://agentdojo.spylab.ai/results/) links execution traces.
  Further trace acquisition and version alignment remain unfinished.
- [AgentDyn v1 preprint](https://arxiv.org/html/2602.03117v1): dynamic tasks and
  useful external instructions overlap directly with the benign-example concern.
  Current [repository](https://github.com/leolee99/AgentDyn) README has a revised
  title/author list relative to v1; do not silently conflate paper versions.
  Actual released traces and code were inspected. The v3 provenance audit separates
  task IDs, text duplicates, payload repetitions and trajectory occurrences. It
  does not yet certify binary labels. One shared template greatly limits attack
  diversity even where user task coverage is broader.
- [RAG-PIBench v1, October 2026 preprint](https://arxiv.org/html/2610.08571v1):
  4,876 rendered examples; reported train/validation/test sizes 2,936/962/978.
  The paper emphasizes protected testing, host/payload provenance and lightweight
  detector baselines. Its methodology renders host passages with embedded
  payloads; that is not evidence of authentic historical user-task alignment.
  Inspected HTML contains no dataset/repository download link found by the current
  review. Article license is not a dataset license. Do not include its data until
  actual artifacts and usage terms can be inspected. This is related work, not
  an available approved source at present.

Local diagnostic sources: [Laya model card](https://huggingface.co/convaiinnovations/laya-multilingual),
[official Ollama System One reference](https://docs.ollama.com/api/systemone), and
installed pinned `laya==0.4.17` source. Laya SDK `agent.py` maps false/true criteria,
returns index-1 probability as noul; `common.py` renders options false then true.
These support probability semantics, not predictive quality. Nimble's Q4_K_M
quantization and Laya's multilingual checkpoint are specific tested implementations;
neither result should be generalized to all full-precision or English-only variants.

## Additional close overlap discovered during artifact review

[Passing the Test You Trained On](https://arxiv.org/html/2610.03448), October 2,
2026 preprint, already compares fifteen detectors with task-aware Qwen2.5-7B and
Llama-3.1-8B judges, and task-aware Sheltron. It studies low-FPR operation,
formatting and training overlap. This is much closer than a generic agent attack
benchmark. Its task-aware results are mixed; adding context is not a new claim.
The v1 judge truncates at 6,000 characters. Native decision probability quality
and coverage-preserving controlled task ablations remain possible distinctions,
pending the updated repository audit; no novelty claim is established.

The [released repository](https://github.com/lzwhehe/benign-instruction-bench),
revision `5d0ae7c438a7b01be2ac0a2e8bc943e45c8f851f`, is MIT for its code/results.
Its current README revises numerical findings relative to arXiv v1 and describes
task-clustered intervals. It also includes no-request judge score files: inspect
these before asserting a missing task ablation. Third-party datasets retain their
own terms; its shorthand description of BIPIA as MIT does not override BIPIA's
component-specific licenses already verified in this project.

Actual collection code inspection (not execution) found:

- `collect_agentdojo_outputs.py` runs original ground-truth calls in the default
  simulated environment. This is deterministic fixture replay, not an observed
  production trajectory or a new model-generated example.
- `collect_agentdojo_pairs.py` labels changed outputs by differential replay.
  It matches call function and position but not exact call arguments; task ground
  truth is separately computed in clean/injected environments. These details need
  checking before inheriting labels. It uses Python hash for attack assignment,
  requiring the documented `PYTHONHASHSEED=0` for reproduction.
- `collect_taubench.py` assigns `task.instruction` as `user_request`. Verify whether
  this is a simulator instruction rather than the assistant's actual trusted
  message before using it as authentic task context. Do not silently conflate them.
  Its added product-name injections are the authors' constructed intervention.

The community [buried-injections](https://github.com/rudratoshs/buried-injections)
repository at `073d1de361ea1c6f45641c129ccf12401110edf2` is MIT. Its actual
`bench/datasets/__init__.py` rotates injection-vector defaults over task prompts,
then appends attacks. That pairing is not an authentic original task/document
relationship. Exclude it from our authentic-context evaluation; retain as related
work about formatting. No upstream scripts have been executed.
