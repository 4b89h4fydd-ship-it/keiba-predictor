# NIDONE-factor research program (2026-11-09)

Research-only candidates inspired by the NIDONE approach, built and
judged under a pre-registration fixed before any fit
(`preregistration-20261109.md` in the goal workspace
`~/workspace/goals/arvexq/hidden_files/nidone-factors-20261109/`).
Nothing here touches production: candidates adjust the v9b
calibrated base at the probability level on identical material and
are judged paired-by-race against (primary) the production final
form and (secondary) a same-material shadow-v9b regeneration, with
day-cluster bootstrap 95% CIs.

## Verdicts (2026-11-09)

| candidate | NAR | JRA |
|---|---|---|
| M1 opponents' subsequent results | **rejected** (◎ −0.016 primary; 1,562-race consistency window bounds any ◎ gain to ≤ +0.6pt; arm C ◎ significantly down) | **rejected** (◎ −0.148 primary; 11% evidence coverage made the fit unstable) |
| M2 pedigree (fixed / career-decay) | **rejected** both arms (◎ unchanged; B36/R24 ROI fell sharply — cheap hits gained, expensive hits lost) | **undecided** (no pool-era pedigree to fit on; primary-window coverage now ~99%, needs ~300+300 accumulated races) |
| M3 course frame/style bias (+frame / +style / +both) | **rejected** all arms (primary-window frame gain reversed to −0.008 on the consistency window) | **rejected** all arms (harmful on both windows, incl. the turf / big-field / short-distance slices) |
| M4 integration | not built — no component passed or held a consistency-clean positive signal | |

Method notes: a candidate whose ◎ falls is not an improvement
regardless of LogLoss (standing rule); period-split consistency is
mandatory (a sign flip across windows = window luck, not a pass);
checkpoints are 100 interim / 300 primary per box.

## Layout

- `build_corpus.py`, `build_results.py`, `patch_pedigree.py` —
  corpus build (day DBs -> sqlite; results universe; pedigree union
  across pin/plain day DB copies).
- `stage0_analysis.py` — Stage 0 inventory / join audit numbers.
- `common.py` — shared machinery: corpus + history access, base
  regeneration replica, candidate construction, paired metrics,
  day-cluster bootstrap.
- `m1_features.py`, `m1_fit_judge.py` — M1 opponents'-subsequent-
  results features (strictly-before-date opponent graph) + fit/judge.
- `m2_features.py`, `m2_fit_judge.py` — M2 pedigree produce/sibling
  aggregates derived from own stored results; fixed vs decay arms;
  career/first-surface/distance/transfer segment reporting.
- `m3_features.py`, `m3_fit_judge.py` — M3 measured course bias
  (ability-controlled residuals, shrinkage, trailing-28d weekly part)
  + frame/style/both arms + pace-overlap check.
- `breakdown.py` — venue/distance/field-size splits + honmei-flip
  failure analysis from the pair CSVs.
- `test_nidone_factors.py` — section-8 suite (15 checks: identity
  collisions, join correctness, leakage/same-day boundaries,
  pedigree missingness, bias sample counts, probability/marks
  invariants, base reproduction, segment exclusions, production
  untouched). All 15 pass as of 2026-11-09.

Stage reports (numbers first, plain words) live in the goal
workspace: `stage0-data-inventory-join-audit-20261109.md`,
`stage1-m1-opponents-result-20261109.md`,
`stage2-m2-pedigree-result-20261109.md`,
`stage3-m3-course-bias-result-20261109.md`,
`stage4-final-verdict-20261109.md`, plus the per-race primary pair
CSVs (`m1_primary_pairs_*.csv`, `m2_primary_pairs_*.csv`,
`m3_primary_pairs_*.csv`).

Scratch data (corpus, features, judgement JSONs, gamma caches) is
under `var/scratch/nidone-factors-20261109/` and is not committed.
