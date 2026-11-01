# Hosted continuation amendment v2.3.2

Luna Responses encountered a saved HTTP 504 gateway timeout with Retry-After 120
seconds. The runner correctly stopped because its bounded in-process sleep limit is
60 seconds. This is transport failure evidence, not an authentication, billing or
quota refusal. The original empty-response STOP and resolution are archived in
`evaluation/luna_chat/stops/` along with the new gateway STOP; the raw failure is
unchanged. The failed cell is retained as invalid and is not retried.

The amended resume guard requires a resolution bound to both the current STOP hash
and exact failed-record hash. It permits only the subscription route, eligible
transient HTTP status, matching finite delay, and an expired delay measured
conservatively from the saved timestamp plus recorded duration. It cannot clear
429, auth, billing or model failures. The previous empty-stream resolution is now
restricted to its original matching empty-response STOP. The per-cell skip remains
unchanged, as do prompts, settings, models, routes and spending caps.

This operational amendment occurs during evaluation and is not a predictive change
or evaluation-based tuning. The Laya v2.3 integration freeze hashes the shared runner,
so a separately saved v2.3.2 integration amendment records precisely the shared
runner change and corresponding freeze-verification change; all original freeze
files remain untouched. The already-running Laya process began under the original
v2.3 check. No local inference implementation or model configuration changes.

Focused tests cover the delay boundary, route/status restrictions and inability of
the old empty-response permission to clear a new gateway STOP.
