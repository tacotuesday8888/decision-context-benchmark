# Results and paper preparation

[Research notes](TEACHER-MEETING-SUMMARY.md) · [Paper outline](PAPER-OUTLINE.md) · [Review corrections](REVIEW-RESOLUTION.md)

## Main results

Arrows show **empty task field → actual user task** on BrowseSafe++, using publisher labels.

| Model | False alarms | Missed attacks | Average of both error rates |
|---|---:|---:|---:|
| Jev | 12.88% → 6.63% | 8.11% → 11.79% | 10.49% → 9.21% |
| GPT-6 Luna (Decisions) | 13.47% → 14.49% | 9.33% → 11.12% | 11.40% → 12.81% |
| GPT-6.1 Sol | 20.68% → 22.69% | 0.80% → 1.00% | 10.74% → 11.85% |

Jev and GPT-6 Luna share 2,850 complete normal/attack pairs. GPT-6.1 Sol uses 498 complete pairs from a 500-pair subset. This is not a matched model ranking. Average error means (false-alarm rate + missed-attack rate) / 2.

**Task information changes mistakes, but does not always help.** Jev made fewer false alarms but missed more attacks. The smaller DTap test gave different results for Sol, so the main finding should not be generalized to every source.

## Figures

- [Experiment design](../../results/paper-preparation/figure-1-design.png)
- [False alarms and missed attacks](../../results/paper-preparation/figure-2-error-tradeoff.png)
- [Task versus three controls](../../results/paper-preparation/figure-3-context-effects.png)
- [Second-source comparison](../../results/paper-preparation/supplement-second-source.png)

[CSV, PDF and SVG files](../../results/paper-preparation/) · [Offline reproduction](../../REPRODUCING.md)

## Status

Results have been checked. GPT-6.1 Sol on Medium reviewed the preparation; its corrections are recorded. Teacher feedback covers only the examples actually read, not the whole dataset. The current paper is not written; no new experiment is required merely to increase the sample count.

Older reviews and page-budget drafts remain as dated records. Use the outline linked above for the current plan. Frozen data, labels and statistical outputs are unchanged.
