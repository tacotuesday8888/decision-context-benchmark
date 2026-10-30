# Reproduce saved completed-arm analyses

These commands make no inference calls. Use the existing analysis environment with
Python, numpy2.4.4 and matplotlib3.10.8. They need the committed raw response records,
manifest, plans and settled per-arm ledger snapshots. They do not need API keys,
model weights or ignored source downloads. Remaining inference arms must finish
before their analysis commands can pass.

```sh
.venv/bin/python scripts/extension_v3/analyze.py --config jev_firstparty
python3 scripts/extension_v3/verify_analysis.py --config jev_firstparty
.venv/bin/python scripts/extension_v3/verify_bootstrap.py --config jev_firstparty
.venv/bin/python scripts/extension_v3/figures.py
.venv/bin/python scripts/extension_v3/reliability_figures.py
```

Substitute `luna_decisions`, `laya_local` `nimble_local` or `luna_chat` for other completed contextual arms.
ProtectAI supports analysis and numerical verification, but has no context contrasts.
The independent bootstrap verifier reconstructs primary and control intervals
using explicit multiplicities and control membership from frozen jobs. For five
completed contextual arms, all81 primary and324 control cases passed, including
insufficient-group cases where an interval must be omitted. Numerical assertions
use full precision; receipt endpoints round to12 decimals for portable serialization.

For a stronger reproduction check, stage intended changes and run:

```sh
.venv/bin/python scripts/extension_v3/reproduce_offline.py
```

It exports the Git index to a new ignored directory, verifies the5793 old file
hashes, reruns all available completed-arm analyses and independent checks, redraws
figures, and requires compared artifacts to be byte-identical. It never exports
`.env.local`, `.secrets` or weights. The receipt records the exact input tree,
commands and artifact hashes. This tests an existing installed runtime, not a fresh
package installation or a new inference run. The latest pass covered27 commands and
53 artifacts for six completed arms, including raw-request/response audits. Later complete arms require a new receipt.

Source reconstruction and model execution are different operations. Their pinned
clones, dependency locks, provenance receipts, source adapters and freeze gates are
documented in the protocol/HANDOFF. Do not run any freeze command again or replace
failed inference cells as part of numerical reproduction. Published fixture text
can appear in retained requests; source-license terms and the documented inherited
label/filter limitations still apply.

Final all-job/accounting closure is separate from completed-arm numerical checks:
`python3 scripts/extension_v3/closure.py --require-terminal` must succeed after all
planned attempts finish. Without the flag it writes only an ignored live snapshot;
it must not be cited as completed execution. Frozen requests include108 development
and11,387 confirmation cells; local diagnostic42 calls are separate and free.

To test deterministic dataset preparation using the pinned local source downloads,
committed inventories and saved AgentDojo replay:

```sh
python3 scripts/extension_v3/reproduce_preparation.py
```

It creates a separate ignored export and copies only source files referenced by
the inventories. It reruns preparation and independent validation, then compares
all five outputs with the frozen originals, including the full prepared text.
The verified run used494 source files and reproduced all five outputs byte-for-byte.
Original frozen files remain unchanged. This is a source-artifact reconstruction
check, not a fresh download or new execution of upstream AgentDojo ground truth.
The replay itself remains bound to its original environment/source receipt.
