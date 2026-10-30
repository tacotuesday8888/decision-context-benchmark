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

Substitute `luna_decisions` or `laya_local` for other completed contextual arms.
ProtectAI supports analysis and numerical verification, but has no context contrasts.
The independent bootstrap verifier reconstructs primary intervals using explicit
multiplicities; control intervals use the same original estimator and are covered
by its tests and point-estimate verifier, not independently recomputed by this tool.

For a stronger reproduction check, stage intended changes and run:

```sh
.venv/bin/python scripts/extension_v3/reproduce_offline.py
```

It exports the Git index to a new ignored directory, verifies the5793 old file
hashes, reruns all available completed-arm analyses and independent checks, redraws
figures, and requires compared artifacts to be byte-identical. It never exports
`.env.local`, `.secrets` or weights. The receipt records the exact input tree,
commands and artifact hashes. This tests an existing installed runtime, not a fresh
package installation or a new inference run. The first pass covered14 commands and
31 artifacts for four completed arms. Later complete arms require a new receipt.

Source reconstruction and model execution are different operations. Their pinned
clones, dependency locks, provenance receipts, source adapters and freeze gates are
documented in the protocol/HANDOFF. Do not run any freeze command again or replace
failed inference cells as part of numerical reproduction. Published fixture text
can appear in retained requests; source-license terms and the documented inherited
label/filter limitations still apply.
