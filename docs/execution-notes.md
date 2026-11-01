# Execution notes

- Owner authorized inference and a US$10 total spending ceiling on October 26, 2026.
  Current pilot routes use free trials/quotas and the existing separately authorized
  ChatGPT subscription. No billing setup, top-up, subscription purchase or recharge.
- Original preparation-only language in historical setup records is superseded by
  this explicit run authorization; smoke records remain historical access evidence.
- `docs/protocol.md`, `data/manifest.json`, the exact prompt, and per-request hashes
  were frozen before any pilot inference. Development checks preceded evaluation.
- Existing ChatGPT credentials were refreshed with their original issued client ID.
  Both Google and OpenAI model catalogs authenticated and listed the requested models.
- For offline reproduction and credential-free CI, the deterministic MIT-licensed
  selected dataset is also saved at `data/pilot.jsonl`. It is byte-identical to the
  selected data extracted in ignored `data/raw/pilot.jsonl`; no example, label,
  prompt, threshold, or request changed. The upstream downloads stay ignored.
- Main-panel development returned eight valid outputs per model. No prompt or
  threshold was adjusted. Evaluation started for Jev and GPT after those checks.
- Gemini's original requested route encountered 503 capacity errors and a transport
  timeout during development. Those are operational failures, not classification
  errors or proof that the model cannot perform the task. Raw attempts are retained.

This file records implementation/execution details without changing the frozen
experimental protocol. Results and any omissions are reported in the final report.

## Completed primary run

- Jev and GPT each completed 80 requests: 8 development and 72 held-out evaluation.
- Jev returned 80 valid decisions. GPT returned 79 valid answers and one incomplete
  evaluation stream whose entire 128-token output budget went to reasoning. That
  invalid counts as incorrect in the primary balanced accuracy, never as a gold NO.
- Gemini 3.8 made 8 attempts across 4 development requests; none produced a model
  answer. Its 16 planned evaluation requests were not run because development failed.
- The separately documented Gemini 3.7 substitute timed out on its first development
  request and stopped. No three-model evaluation completed.
- Total: 169 HTTP inference attempts and 165 saved per-example/condition records.
  Both free Gemini routes remained unavailable. No paid API fallback was used.
- Jev used 51,786 reported input tokens; its final reported free balance was 47,935.
  Added paid API spend was US$0. Subscription usage is reported as tokens, not assigned
  a fictional marginal API price.
- The selected MIT dataset is tracked for offline reproduction. All 165 raw records
  and the unified structured table are included; complete upstream downloads, historical
  raw smoke captures, and credentials stay local/ignored.
- Integrity validation checks the original frozen hashes; usage extraction also reads
  terminal incomplete-stream metadata without changing its invalid prediction.
  Operational additions after development (a gate blocking failed-development models
  from evaluation and credential-free selected-data packaging) changed no requests.

## Reproduction and analysis qualifications

Pre-inference character-count estimates were computed in a separate command after
freezing: 151,178 Jev request characters (~37,794 tokens at chars/4), 162,378 GPT
characters (~40,594 tokens), and 41,765 Gemini characters (~10,441 tokens). These were
approximations, not provider-tokenizer or billing estimates. The frozen protocol's
statement that freeze prints those estimates refers to this preflight sequence; the
`--freeze-only` command itself prints request counts. The saved exact requests make
the character counts independently reproducible. The separate byte-count guard was
conservative and kept Jev well within its free balance.

The primary experiment uses one response per cell, without matched sampling seeds.
Bootstrap intervals concern the selected example groups, not model-generation noise.
The exact GPT response ID is `gpt-6-luna`; no immutable underlying weights revision
is independently available. Provider-returned sampling and reasoning defaults are
extracted into the summary, including usage from the incomplete stream.
