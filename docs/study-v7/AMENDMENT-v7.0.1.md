# V7.0.1 — development metadata parser and safe continuation

Recorded November 1, 2026, after the first development batch stopped and before
any confirmation request. No prompts, source labels, selected examples, groups,
conditions, model IDs, reasoning/output settings, payload bytes, budgets or
statistical procedures change. Request plan remains
`ad3a9b1bcbad2ebc3f4337673b45ddc0ddf05855cf06a70dccb2b473c99af815`.

The first batch completed13requests:5Jev,4Luna Decisions and4Luna Responses. All
four Responses calls returned HTTP200/completed with the requested model, output
cap256, reasoningnone, default tier, storefalse and no input truncation. Their
cache metadata was `{"mode":"explicit","ttl":"30m"}`; cached/write tokens
were zero. The original parser compared that object with `{"mode":"explicit"}`
and marked it mismatched. The [official cache documentation](https://developers.openai.com/api/docs/guides/prompt-caching)
defines30m as the default when TTL is omitted. This was an overly strict metadata
comparison, not evidence that requested caching settings were changed.

Parser `study-v7-routes-2` now accepts exact explicit mode with absent TTL or the
documented30m default. Changed mode, changed TTL or unexpected metadata keys still
fail. The request stays byte-identical; no field is silently removed or substituted.
Original response bytes and completed/parsed records remain immutable. A separate
development-only reparse sidecar binds the original evidence hashes and the new
parser/manifest and records the technical resolution. It does not relabel examples,
change confirmation admission or create replacement attempts.

At the stop, known v7 settlements were $0.0035761OpenAI/$0.000608202TypeSafe.
Unsent reservations held another $2.9405632/$0.004032. There were no unknown-usage
or in-flight entries. These conservative amounts are not invoice balances; the
much larger all-in reserved total must not be called actual model spending.

The original `execution-v1/stop.json` is preserved. The new authorization binds
its exact hash in `acknowledged_stops` and uses a new immutable stop-record name.
Any changed, missing or unacknowledged stop blocks execution. The same journal,
provider caps and phase allocations continue; no held charge is released by this
amendment. Settled/completed requests are never resent. Only original unsent
first attempts can be dispatched, retaining the original schedule order.

Focused offline regressions verify default TTL acceptance, rejection of actual
changes, stop/acknowledge/resume without replay, preserved stop bytes/unknown
holds, and blocking on a new stop. Confirmation remains gated on the completed
development operational receipt and a separate final freeze.
