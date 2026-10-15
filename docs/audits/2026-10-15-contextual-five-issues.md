# Five prediction and mark issues: candidate implementation

Base: fce68c0. Production scorer, browser engine, archived forecasts and bets are unchanged.

## Changes ready for paired evaluation

- Replace the fixed blend in the challenger with a bounded distance/field-pressure blend. Historical matching weights consider surface, distance, track, going, recency and observed opponent level.
- Evaluate win tendency from weighted historical wins separately from aggregate ability. Do not label the resulting score a calibrated hit rate.
- Evaluate the axis independently from weighted podium evidence, performance variability and projected early competition. Require at least three dated observations and complete race inputs.
- Give first, second and third slots separate evidence heads; allocate ○ using first/second tendencies, ▲ using second/third tendencies, and △ using third tendency. Calculate joint order weights without replacement and check normalization.
- Require ☆/注 evidence to be reproducible in the current surface and a distance within 150m. ☆ also needs historical finishing gain, front competition and a compatible historical running style. Do not force special marks when proof is missing. Displaced ordinary marks are reallocated by their respective roles.

These choices are hypotheses, not established precision improvements. Unknown inputs remain unknown. Existing official JRA margin and flat/jump separation requirements remain in force.

## Verification

27 Python unit/regression tests pass. Tests cover leakage from future history and target-race result payloads, missing margins, role differences, matched going/opposition, reproduction conditions, normalized joint weights, and insufficient validation samples. Existing live JRA and NAR Node betting smoke checks pass.

## Adoption gate

The comparison workflow retrieves 28 completed days, replays the baseline and candidate on identical eligible cards, splits whole dates chronologically, and evaluates JRA and NAR separately. It requires at least 30 paired holdout races in each circuit, no regression in win/axis/○/▲/△/podium coverage metrics, improvement in a primary metric, and at least ten ☆/注 selections from each method without precision regression. Any failed retrieval blocks adoption. Passing this preliminary gate permits browser parity validation, not immediate production deployment.

This is a retrospective replay with date-bounded historical starts, not a reconstruction guaranteed to match every original pre-off input. A successful result would still require verification against immutable pre-off evidence and browser/Python parity before production.

## Access history

Direct API request from this environment returned HTTP 403. Git push was initially rejected by automatic approval review. The user subsequently explicitly authorized publication of these changes to the public repository and execution through deployment after successful validation. Shell Git has no configured write credentials, so publication uses the connected GitHub account. No production modification is included in this candidate.
