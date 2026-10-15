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

## Executed comparison and correction

Published as draft PR #193. The full repository validation workflow passed on e3c2e3d and 5b411d88. The first comparison incorrectly used compact day-index inputs. API storage code confirms that those indexes intentionally omit full history. The comparison now restores hash-verified repository originals or the full saved race API; restoration tests cover corrupt input and wrong race identity.

The corrected API run (Actions 38734851420, 2026-09-17 through 2026-10-14) retrieved 1,286 cards without retrieval errors. Only three NAR cards had complete observations; 1,282 lacked the required inputs and one lacked a final top three. JRA had no eligible comparison. The initial combined candidate failed the gate: in the two late-period races, baseline versus candidate ◎ wins were 0 vs 1, axis podium hits 2 vs 2, ○ top-two hits 2 vs 1, and podium coverage 6 vs 5 of six horses. This very small sample is diagnostic only, not evidence of a validated gain.

Component testing identified an input-meaning bug: all three eligible API cards had an empty target surface. The candidate incorrectly treated unavailable reproduction context as negative proof and removed ☆/注. It now skips that experimental demotion when target surface/distance is unavailable, exposes component eligibility, and never invents a surface. On exactly the same late-period inputs, podium coverage returned to 6 of six, while ○ remained 1 vs baseline 2. The candidate remains rejected. Ablation testing also found and fixed a research allocator bug that could duplicate special marks when evaluating only the axis component. No live authority was altered.

Read-only official evidence recovery uses the existing JRA/NAR parsers, exact earlier start references and immutable input hashes. Both methods receive identical recovered historical observations. Newly recovered data is checkpointed separately; original snapshots, D1 and pre-off seals are never overwritten. JRA source timeouts and bounded-run coverage remain adoption blockers. Current verification: 35 tests pass (candidate/observed-authority/special-mark/circuit and pre-post consistency), plus existing JRA/NAR browser betting and independent-axis smoke tests. The shell's initially missing BeautifulSoup dependency was installed from the existing requirements and the previously blocked scheduled-prediction tests then passed.
