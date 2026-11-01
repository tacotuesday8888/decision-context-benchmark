# V7.0.6 token-rate pacing

This is an outcome-blind operational amendment after the first3,209native
confirmation attempts. It changes request timing only. The plan70d860..., source
selection and labels, cohorts/order, request payloads, models/settings, statistical
methods, full-context monetary reservations, caps and14:00UTC admission deadline
remain unchanged. No prediction accuracy was read or used to select this change.
The original confirmation manifest and both stopped jobs remain preserved.

## Cause and retained evidence

The second core stop is a LunaDecisions HTTP429, not another504. The response
reported a2,000,000token-per-minute limit,1,990,581used and10,835requested, with
Retry-After1second and4,999requests remaining. This identifies a token-rate
bottleneck. The failed first key2c20194b... remains invalid/missing and will never
be resent or replaced. Its full0.525reservation remains held as unknown usage,
separately from the earlier504's0.525hold. No billing change or hold release occurs.

The last groupbrowsesafe-v7:28631 admitted16requests:9terminal,7reserved but never
sent. The continuation finishes those7 before admitting the next frozen group.
The preserved v5 stop hash is2e10a2bc779bc3f4a84532b38d4d15a914ca1e948aaa07a20952a9d8a37e2f5c.
All completed/unknown first attempts, stop bytes and journal prefixes remain.
Sol remains operationally deferred; its latest pause is not acknowledged.

## Shared quota gate

LunaDecisions and LunaResponses share one thread-safe rolling60second gate.
Before durable dispatch intent, each concurrent request reserves
`max(1024,ceil(2*serialization_proxy_tokens)) + output_cap`, where output_cap is256
for paidResponses and0for nativeDecisions. The soft total is1,500,000tokens per
rolling window, below the observed provider2,000,000limit. Jev/local/Sol do not
consume this particular gate. Existing four-worker whole-group scheduling stays.

The token proxy is the already frozen serialized-JSON o200k count, bound by its
exact token-audit-v3 file hash and each current request/payload hash. This is a
pacing heuristic, not a proven native token upper bound or a new cost estimator.
Full accepted-context monetary reservations remain authoritative. A quota failure
still produces a terminal first failure and stops for review; no automatic retry.
The maximum planned request allowance is50,650, below the soft total. Oversized
or malformed estimates must fail explicitly before dispatch rather than deadlock.

Every newly created gate/process waits a full60second startup cooldown. Prior
phase futures have joined before a following phase starts, so this also prevents
a fresh repeat process from ignoring recent confirmation traffic. Rolling
reservations then use a monotonic clock, include concurrent dispatches and are
never refunded for errors/unknown usage. Waiting occurs outside ledger locks and
checks cancellation before dispatch. Metadata-only pacing events contain no
source text or credentials. Monetary policy and append-only accounting do not change.

## Usage-only check and limits

The independent check used2,104native and500Responses usage records, not scores,
predictions or labels. Native actual-input/proxy weighted ratio0.9567851 and
maximum2.1153846; the ratios above1.5 occurred only on tiny external inputs, covered
by the1,024floor. Responses maximum was0.9871568. The chosen allowance covers
input plus paid output for every observed record, with zero observed violations;
maximum actual/allowance was0.600372native and0.490352Responses. This is empirical
headroom, not proof for unseen inputs or concurrent traffic outside this executor.

Both prior token-audit versions match all35,200current paid Luna request keys and
payload hashes. The currentv3 audit is used. The remaining nominal allowance is
about293.76milliontokens, implying at least195.8minutes of rolling-window pacing.
Provider latency, the full local windows and other overhead add time; completion
of the full target before the fixed deadline is not guaranteed. No samples will
be replaced to achieve a target. Missing cells and attained prefixes stay explicit.

The refreshed execution manifest binds the gate code, integration, proxy file,
unchanged plan/statistical hashes and usage-only calibration. A new owner receipt
acknowledges exact old stops, retains unknown holds, and uses a distinct new stop
name under the existing owner window/caps. No purchase, payment change, recharge,
reset, paid Sol fallback, new model, source refill or paper writing is introduced.
