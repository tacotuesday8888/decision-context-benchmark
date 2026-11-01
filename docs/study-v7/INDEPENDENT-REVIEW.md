# Independent preparation check

Read-only helper `/root/independent_review`, November 1, 2026. This was a separate
Codex agent with shared project context, not human peer review or an independent
empirical replication. It made no model calls, loaded no weights, and inspected
no confirmation predictions or correctness.

The reviewer independently checked original source bytes/labels/provenance,
historical and cross-source exclusions, exact rank selection, the reconstructed
main graph, 200development/3,000confirmation groups and the100-group audit packet.
It checked PromptShield's4,000test/100validation requests and nested1,000subset.
The exact request-plan hash is
`ad3a9b1bcbad2ebc3f4337673b45ddc0ddf05855cf06a70dccb2b473c99af815`:
64,500paid API +6,000subscription +5,200local records.

It independently reproduced the corrected forecast scenarios
$21.406249644/$41.324364444/$83.309528888 and accepted-context maximum
$16,661.709920. It retokenized all5,200local documents with the pinned Transformers
tokenizer, explicitly disabling truncation/padding; every count matched the
corrected audit, totaling16,048windows. Per-condition token sums and paired
task-minus-length deltas also matched (about9.15local-proxy tokens on average).
This does not establish a native Jev/OpenAI tokenizer match.

Hand-computable t/Holm/bounds fixtures, synthetic validation interpretation and
23execution fixtures passed its check. Review findings led to corrections before
any inference: complete historical-component document screening, individual prior
AIB messages, external mixed-label allocation, price-tier/hash consistency, full
tokenizer windows, narrow ledger reads, overflow/unknown-hold policy, explicit
subscription/payment guards and crash-recovery replicate/stop consistency.

The reviewer also flagged clean reconstruction of the earlier external-v2 raw
filename. `recover_external_alias` now restores it only when the current v3 bytes
match both pinned selection-lock hashes; a regression verifies changed bytes are
refused. Existing selected bytes and all cohort hashes remain unchanged.

Remaining limitations are operational native-token/access/credit/rate checks,
provider-default subscription output ceiling, semantic and private-training
overlap, and the documented missingness assumptions. These are reported in
[READY-TO-RUN.md](../../READY-TO-RUN.md) and must not be described as verified model
performance or full-corpus semantic independence.
