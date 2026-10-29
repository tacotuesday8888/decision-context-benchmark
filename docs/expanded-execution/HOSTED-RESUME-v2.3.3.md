# Hosted overload continuation policy v2.3.3

Astra stopped after 772 saved logical cells: the task cell for
`llmail:phase1:3f93a12a-36d2-4be9-9408-3bc18e4a49ef` returned HTTP 200 with a
provider failure code `server_is_overloaded`. The raw record is
`44dec52133fc4bb830577a29-0.json`. This is a transient service failure, not a
classification, quota, authentication or billing refusal. Preserve the record as
invalid and do not repeat it. Only the 40 unattempted cells remain eligible.

The continuation policy requires the exact STOP and raw-record hashes, matching
candidate ID, Astra subscription route, HTTP status and provider failure code, plus
120 seconds elapsed after the saved timestamp and measured duration. It rejects
quota/rate-limit/authentication errors and API-key routes. A later STOP cannot reuse
this hash-bound resolution. If another stop occurs, preserve it and assess its
actual cause; this is not an automatic retry loop.

This operational policy is frozen before continuation. The shared runner remains
v2.3.2 with unchanged bytes; only its separately imported STOP-resolution policy is
extended. The original v2.3.2 policy snapshot and every original preparation/local
freeze remain untouched. The companion v2.3.3 snapshot identifies the exact helper,
tests, failure and resolution used. No inference prompt, model setting, route,
threshold, label or budget changes. No failed cell is rerun.
