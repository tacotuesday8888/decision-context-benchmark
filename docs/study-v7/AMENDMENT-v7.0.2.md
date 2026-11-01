# V7.0.2 — explicit subscription cache limitation

November 1, 2026, before any confirmation request and before a valid Sol
classification response. Core development is complete:500Jev,500Luna Decisions,
500Luna Responses and200ProtectAI records. No accuracy was used for this change.

The Sol subscription endpoint rejected four requests with HTTP400,
`invalid_parameter`, parameter `prompt_cache_options`, stating that the parameter
is unsupported on this model. Its lane paused and four admitted unsent zero-cost
reservations remained. This is a parameter incompatibility, not an allowance or
credit failure. No reset or paid fallback is used. Original responses, requests,
pause record and journal entries stay immutable.

The explicitly named `sol_subscription` revision **v7.0.2** omits that unsupported
field. Its caching is now **provider default/uncontrolled**, recorded in model
metadata and returned usage; it does not claim the paid route's explicit-only
cache control. Output cap remains unsupported/provider default. Model
`gpt-6.1-sol`, reasoninglow, strict output schema, complete stateless input,
storefalse, streamtrue, default tier and the public project-OAuth route stay fixed.
The fresh authenticated catalogue reports default context500,000 and maximum
872,000tokens; use the conservative default without experimental context.

This is a separately preserved request plan. All **69,700non-Sol request records
and payloads** are identical. For all6,000Sol requests, source IDs, tasks/pages,
questions, conditions, groups, subsets, order purposes and every other payload
field are identical; the sole payload difference is the omitted cache option.
The equivalence receipt binds both plan hashes and these checks. The old paid/
subscription configurations and their unsupported attempts remain in history.

One explicit offline journal amendment replaces only zero-cost Sol development
schedules before any confirmation schedule exists. It archives the old schedules
and counters, preserves completed failures, and cancels only the four positively
unsent zero-cost reservations. The new schedule keeps the same group order/counts
with distinct payload keys and revision-specific batch IDs. The provider policies,
caps, paid entries, costs and unknown holds cannot change. No active executor may
hold the process lock during this operation. Reopening/repeating the same amendment
is idempotent; incompatible amendments are rejected.

The new owner receipt acknowledges the exact old pause hash and uses a fresh
pause-record name. Any changed or new pause is preserved and stops Sol alone.
This is one bounded compatibility amendment. **If another required subscription
parameter is unsupported, defer Sol and the Sol audit; do not enter another
parameter-fixing loop or use paid Sol.** Cheap/native confirmation can proceed
after its operational receipt and final freeze under the original bounded scope.

Native/Luna paid inputs, fees, local windows, source labels, cohorts and primary
statistics are unchanged. Forecastv3 reuses only verified identical measurements
and retokenizes the revised subscription payloads. The earlier four Luna metadata
records receive a newly bound development-only reparse sidecar; their actual calls
and original bytes are not repeated or overwritten. The final confirmation freeze
must name this revision, its default-cache limitation and any unsupported route.
