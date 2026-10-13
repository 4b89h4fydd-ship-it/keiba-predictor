# Sealed conditional ranking challenger — actual run (2026-10-14 JST)

Research-only Python implementation: `scripts/arvexq_sealed_conditional_challenger.py`.
[Successful Actions run](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38444449774), archived evidence [artifact 11837372745](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38444449774/artifacts/11837372745).

- Retrieved day API records for 2026-10-07 through 2026-10-13: 396 races.
- Eligible genuine pre-off seals with all four historical probability heads: 235.
- Train 54 races (October 7–9); candidate selection validation 73 races (October 10–11); later comparison 108 races (October 12–13).
- Selected on validation alone: P1+P2+P3 conditional-logit challenger, L2 0.05, coefficients 0.6045684744, 0.2843691238, -0.1685090788.
- On 108 later races: saved-decision baseline log loss 2.1126565, Brier 0.8364124, top1 27.78%, winner top3 56.48%.
- Candidate: log loss 2.1509048, Brier 0.8452476, top1 27.78%, winner top3 56.48%.
- Candidate–baseline log loss +0.0382483; race-bootstrap 95% interval [+0.0091465, +0.0698088] with 2,000 resamples.
- **Rejected**: both proper scoring rules worsened; furthermore this short later comparison had been inspected previously.
- These are *historical saved v317 predictions*, not an independent audit of today's 45/35/20 production system.
- Full machine-readable report in the workflow artifact; no result labels were used to generate prediction features.
- Production ranking, marks, odds, bets and archived originals **untouched**.

New forward-looking candidates must be evaluated using timestamp-proven frozen current-engine inputs and truly fresh later race outcomes; avoid reporting fitted 235-race in-sample score as real-world improvement.
