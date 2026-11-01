# Data and access

| Study | Source | Selected data |
|---|---|---|
| Earlier comparison | AgentDojo, AgentDyn, InjecAgent | 761 task–text combinations; 582 distinct texts and 138 tasks |
| Main comparison | BrowseSafe++ | 3,000 normal/attacked page pairs; 6,000 page versions |
| GPT-6.1 Sol follow-up | The same BrowseSafe++ selection | 500 of those pairs, not additional independent data |
| Supporting detection test | PromptShield | 4,000 texts |
| Second-source check | DTap | 66 pairs; 62 shared complete pairs |
| Action pilot | Authored for this project | 12 synthetic tasks |

The main Jev/Luna comparison uses 2,850 shared complete pairs; the Sol comparison uses 498 complete pairs. Not all models ran on every source. Counts overlap and use different units, so they must not be added into one sample size.

## What a clone contains

Saved tables, figures, protocols, code and verification receipts are tracked. Some early released-fixture records are also tracked with their notices. Restricted source downloads, current full raw evidence, human-review material, credentials and model weights stay ignored. Do not assume every file needed for every historical command is included.

BrowseSafe++ contains privacy-rewritten pages; this project's evaluation selection comes from the released training partition, not the official test partition. Labels are supplied by the sources rather than independently verified human ground truth. Published benchmarks can themselves contain constructed attacks.

## Provenance and permissions

- [Earlier source selection and methods](docs/extension-v3/PROTOCOL-v3.0.md)
- [Main grouping and selection](docs/study-v7/DATA-PREPARATION.md)
- [Second-source eligibility](docs/subscription-followup/SECOND-SOURCE.md)
- [Source comparison notes](docs/critical-review/METHODS-NOTE.md)
- Existing notices: `docs/third-party/` and `docs/expanded-v2/third-party/`.

Dataset access terms and licenses remain source-specific. Source-containing files retain their original licenses and attribution. AgentDojo, AgentDyn and InjecAgent MIT notices are in `docs/third-party/`; BIPIA, LLMail and control-source notices are linked above. Restricted downloads and private review records are not included. No blanket license over third-party data or paper DOI is claimed.
