# Why the sealed-head candidate degraded (2026-10-14)

Actual [Actions run](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38445595141) and [machine report](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38445595141/artifacts/11838048499).

## Measured failure, 108 October 12–13 races

- Loss worsened in 65 races, improved in 41, unchanged in 2.
- Central racing: 16 worsened /22 total, mean added winner log loss **+0.1140**.
- Regional racing: 49 worsened /86 total, mean added winner log loss **+0.01886**.
- For winning horses assigned under 10% by the previous predictor: 34/42 worsened; for 10–25%: 22/41 worsened.
- October 12: added mean log loss +0.07065; October 13: +0.00336.
- Kyoto 2R October 12: true winner #11 predicted 26.46% before vs 16.30% after.
- Obihiro 9R October 12: true winner #3 predicted 4.35% before vs 2.29% after.
- Original conditional head coefficients: +0.60457 P1-vs-decision, +0.28437 P2-vs-decision, -0.16851 P3-vs-decision. These coefficients shift mass from original decision probabilities: they are NOT distinct measured changes in horse latent ability.
- Held-out original baseline log loss 2.11266 vs challenger 2.15090, Brier 0.83641 vs 0.84525, unchanged leader-win 27.78%.
- **Confirmed mechanism:** probability mass transferred from actual winning runners, disproportionately among Central and original low-probability winners. Dataset shift, head correlation, and uncalibrated per-rank probabilities are plausible *causes* but not independently causally identified here.

## Tested mitigation and outcome

Research-only script tests 0%, 10%, 25%, 50%, 100% coefficient application, several L2 penalties and head subsets. Baseline/zero-adjustment is an explicit fallback. Both validation log loss and validation Brier must improve by more than configured margins before adopting a candidate **in the experiment**.

**The validation gate alone was insufficient**: the original full adjustment still passed that gate, and still degraded October 12–13 results. Thus shrinkage / prior validation is NOT evidence of any real remedy. No corrected model promoted. This historical period has already been inspected; fresh pre-off independent data and separate JRA/NAR diagnostic gates are required for model promotion.

No original locked forecasts, marks, odds, bet selections, or actual production model were modified.
