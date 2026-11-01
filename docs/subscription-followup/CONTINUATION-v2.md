# Core continuation v2 — observed availability failure

This is a postcollection operational amendment, not a new scientific analysis or
an invisible retry. Core v1's code, manifest, stop, ledger and raw outcomes stay
unchanged. No label correctness, accuracy or target effect was inspected to choose
the continuation.

At15:05:39UTC a public Responses stream returned HTTP200 but terminated with
`response.failed`, model`gpt-6.1-sol`, `error.code=server_is_overloaded`,
`error.type=service_unavailable_error`, no usable usage, curl exit0. The original
rule recognized transient HTTP5xx but stopped for other terminal failures. It
correctly sealed at15:05:47UTC after464 actual first attempts:10 preflight,
453 valid main answers and one failed main answer. Three already-dispatched
valid outputs settled after the failure. This is availability evidence, not a
wrong answer, authentication failure or verified exhaustion of subscription quota.

The old journal SHA256 is
`05cf42e643a72dc0d248f593d46fddcea41b40d5b81315f5c71dce2999420426`.
All464 dispatched cells stay first outcomes. Ten additional reservations were
positively cancelled before dispatch; their attempt directories do not exist and
the immutable cancellation evidence binds their terminal entries. Another4,036
original cells were never admitted. V2 admits **only this4,046-cell unsent
complement**:3,546 main,400 repeats and100 reviews. It never re-admits a dispatched
cell, including the overload failure. All logical IDs, source rows, labels,
payload bytes, order and analysis contract remain from the original4,510-cell plan.
Partial groups retain their original completed members for final analysis.

The new ledger distinguishes prior actual attempts, proven unsent cancellations
and never-admitted cells. Its exact roster and cumulative stage quotas include
the464 old calls; it does not create another4,510-call allowance. Total general
calls across both series stay at most4,410 and review calls100. Original
ten-cell technical validation is hash-bound and reused without additional
preflight inference. New API dollars remain zero, and all inherited TypeSafe
spending/holds remain unchanged.

The clock is anchored at the **original14:57:56.429131UTC** start. New admission
and dispatch end at **19:57:56.429131UTC**; a new process/namespace does not reset
the window. A new stream overload may trigger bounded availability continuation
only when every observed field above matches exactly. Actual HTTP200 and error
code remain in raw evidence/runtime events; they are never rewritten as HTTP503.
All other failures retain the original fatal rules. The old overload consumes
one of the maximum five transient-failure events. The same three-consecutive
failure rule, provider Retry-After bound and no-retry rule continue. At least120s
from the recorded overload must elapse before a new request.

V2 starts in a fresh directory under an exact reviewed manifest. Any later process
restart with prior v2 attempts or entries fails closed for offline reconciliation.
The current owner instruction to finish feasible work authorizes this bounded
operational continuation; no purchase, API-key fallback, quota bypass, original
v7 reopening or scientific sample replacement is authorized.
