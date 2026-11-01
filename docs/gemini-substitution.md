# Bounded Gemini availability substitution — recorded before inference

October 26, 2026. The planned Gemini 3.8 Flash route repeatedly returned 503 capacity
errors and a timeout on development examples. Do not use its failures as detection
scores. Try catalog-listed `gemini-3.7-flash` through the same existing Google project
with no billing configured, as an explicitly named substitution. No paid fallback.

Use the original frozen decision prompt, settings (temperature=0, maxOutputTokens=128),
development examples, and the four evaluation IDs already selected for Gemini in
`results/pilot/frozen-plan.json`. This preserves the sampling and question before any
substitute-model evaluation. Maximum 20 attempts including errors, at least 13 seconds
between starts, no retries. Stop immediately on any non-200 response or an invalid
DEVELOPMENT result. Evaluate only after four development outputs pass completion,
format and returned-model checks. Do not change prompts or thresholds.

Save every exact request, response, timing, usage, model version, error and gold reference
under `results/pilot/gemini-3.7-records/`. This supplementary route is distinct from the
original frozen v1 records. Compare all providers only on the same four evaluation
candidates with complete condition coverage. Use the same paired cluster bootstrap and
invalid-response rules. If availability fails, keep the completed two-model primary
pilot and report the missing supplementary comparison. Do not claim a completed
three-model panel unless actual substitute responses exist.
