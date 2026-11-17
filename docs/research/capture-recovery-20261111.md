# Capture completeness repair and recovered forward evidence

## Executed recovery

User explicitly approved model export. Flight521f0ebb-f721-4818-89f2-d60bc6ec8b8b
version10/run8 succeeded. Six NAR estimators,vectorizers and scorecards were
retrieved to `/workspace/arvexq-research-models`. SHA256 of models.tar.gz:
`bf7ecfbaf4b84402f06e0b3451c8853a59c07ed97e8b5c5b5b1956ab1370cd3c`.
No model file was committed to the repository or installed in production.

The earlier data inventory omitted independent Actions capture artifacts.
Inspecting100 capture runs and recovering57 nonempty artifacts produced145
unique pre-off races after validating recordHash,featureHash,capture<post,
excluding Banei,and choosing the latest capture at least5 minutes before post.
20 capture observations within5 minutes were excluded. Artifacts are preserved
at `/workspace/arvexq-research-data/preoff`,with chosen immutable records and
separate result joins. Their source remains provisional; matching hashes alone
does not independently attest an official roster.

MotherDuck had42 of these races with unsettled/missing results. Read-only D1
retrieval recovered38 settled result payloads,stored separately in
`result-repairs`; no feature or production table was overwritten. After exact
frozen-roster and paired-market checks,77 races/895 horses were usable across
both circuits.21 races had partial rosters,4 remained unsettled,43 failed other
paired completeness/podium checks. These counts explain why145 records do not
mean145 valid model evaluation groups. Existing source payout objects have not
been independently reverified against official raw publications.

## Root causes established

1.Data discovery/lineage: Actions pre-off artifacts had not been included in the
MotherDuck-only training inventory. This was a real omission in the prior work.
2.Result synchronization:38 settled D1 results were absent/unsettled in the
MotherDuck snapshot labels. Recover them as separate labels,never inputs.
3.Schedule coverage: recent successful GitHub runs were hours apart despite
10-minute cron settings. A35-minute collection horizon loses races between
runs. Scheduler success was not a completeness measure.
4.Silent truncation: default max_races12 could silently omit additional due
races. Default is now unlimited; explicit caps report deferred race_ids.
5.Retention:30-day artifacts expire; extend existing workflow artifacts to90
 days.90 days is not permanent archival; research tables provide separate
append-only storage when the on-demand capture Flight runs.
6.Temporal correctness: the old collector reused its start-of-run time after
HTTP retrieval. Recheck the actual clock immediately before sealing; never
pretend a late response was observed before post.
7.Source information: legacy captures lack original v9b/R24 publication and
raw pre-off detail. Preserve both separately in future captures. Do not infer
past baseline bets from current post-race predictions.
8.Data quality:partial result labels shrink frozen rosters; missing position/
closing aliases and NAR/JRA class normalization were repaired in prior steps.

## Active collection repair

Collector-only PR515 merged as86451816; no prediction engine/ticket/API/D1
change. Capture all currently listed upcoming races in the day,not just35
minutes; remove the default race cap; retain raw pre-off data and comparator
publication outside features; exclude Banei; expose deferred IDs; return failure
on partial collection; retain compressed Actions artifacts90 days.16 collector
contracts passed,including late network response,no cap,and Banei tests.

MotherDuck Flightd2b9a3a6-0836-4269-a28d-fcb0f7e5d0f6 version2/run2 succeeded.
It processes/persists races individually rather than retaining the entire day
in RAM. Nov11 source API roster48,pre-off captured48,failures0. Confirmed48
unique records in `my_db.arvexq_analytics.research_preoff_captures`.
`research_capture_runs` records run heartbeat,counts and failures. Both are
research-only append-only tables; training_eligible=false. A private MotherDuck
Guide documents their lineage and limitations.

Actual plan limitations:MotherDuck rejected scheduled Flights (Business plan
required),and rejected F16 for a new Flight (onlyF4 available). The working
capture Flight is F4,on-demand; it is NOT a running five-minute timer. GitHub
scheduled capture is active but best effort. Do not claim guaranteed full
coverage or autonomous permanent MotherDuck refresh. Source API completeness
against all official scheduled meetings is still a separate verification task.

## Fixed-model forward replay

The six already-fitted NAR models were not retrained or tuned on recovered test
outcomes. Calibration:Nov4–5,6 races. Test:Nov6/10,5 races on2 dates. Other days
were filtered by source/label/roster/market availability. Outcomes were joined
only after the frozen inputs. These are newly scored later-date research races,
but the capture source is still provisional,not an adopted certified benchmark.
These calibration/test dates are now consumed and must enter future holdout
ledgers. Script:`scripts/replay_recovered_preoff.py`. Full report:
`recovered-preoff-forward-evaluation-20261111.json`.

|Model|Top1 win|Top1 podium|Winner Top3|NDCG@3|MRR|
|---|---:|---:|---:|---:|---:|
|Ability|20%|60%|20%|0.4110|0.3400|
|ANA|0%|20%|0%|0.1767|0.1808|
|Pointwise|0%|20%|40%|0.3800|0.2952|
|XGBoost|20%|40%|60%|0.4425|0.4182|
|Winner LTR|0%|60%|60%|0.4785|0.2515|
|Podium LTR|0%|40%|60%|0.4375|0.3167|

Win probability calibration is fitted only on calibration dates. Report stores
before/after LogLoss,Brier,ECE and calibration bins,podium Brier,temperature
choices,and paired date bootstrap. XGBoost win-hit difference versus Ability
95% date-bootstrap interval[-0.5,0.3333];no improvement established.

Stored-payout shape/finisher-reconciled flat100-yen bets,5 races per model:
Ability win ROI276%,place68%;XGBoost win50%,place42%. Remove each strategy's
largest payout while retaining all stakes:win ROI0% for both. Ability's single
large win explains the apparent profitable return. Other win ROI0%;place ROI
ANA0%,Pointwise20%,winner72%,podium40%. These are stored-payout calculations,
not independently reverified official-paid-out performance or commercial R24.
Original R24/B36/v9b publications remain unavailable for these old captures.
Do not manufacture those comparators or alter production selection thresholds.

## Decision

New acquisition,model storage,calibration/replay and stored win/place payout
calculations were executed. No robust model improvement,no production adoption.
Keep v9b/R24. Central still lacks a complete independent training/calibration/
test sequence under the fixed minimum and source constraints. Operational
schedule entitlement and irrecoverable historical pre-off fields cannot be
made complete by reporting them as passed. All recovered evidence is retained
for further verified source reconciliation.

## Final runtime checks and correction to selection documentation

main collector run42952066279 completed44/44 currently upcoming source races,
0 failures,retaining a14,100,788-byte gzip artifact. Four earlier races were
already covered by the48-race early MotherDuck capture. Both are observed
source subsets,not independent official-universe completeness claims.
Research integration3c5ad7d3 passed Actions42952729185 and42952725162;
67 local tests +8 subtests passed before the final missing-field-size guard.
Six model artifacts are now actually retrieved,closing the previous export
blocker after user approval. No new permission request was needed.

The morning-picks static archive was also checked:Nov10 has genuinely versioned
v9b ticket evidence,committed09e5f93 at01:55:19Z. However none of the five replay
test race_ids has ticketEvidence in its corresponding morning manifest. Thus
there is NO same-cohort v9b original for that comparison; this is not a blanket
claim that all historical v9b evidence was lost. A future evidence join must
inspect these static manifests rather than only top-level MotherDuck model names.

Earlier documentation listed the80%/30-sample/Wilson65% helper as the current
selection policy. That is incomplete. `rank_selection.js` has aNov11 policy v2
requiring matching v9b model/receipt hashes,prior approved-out-of-sample policy
evidence,timestamps,1–3 valid nonduplicate wide tickets,hitProbability>=.70 and
stressExpectedReturn>=1.05. Legacy Nov10 morning entries use older popularity
selection. Do not pool different policy versions or change these rules here.

Final source guard:future form/position quality no longer invents fieldSize
from finishing/corner rank. Without an observed fieldSize>=2,quality is missing.
Existing frozen matrices remain unchanged; no historical accuracy gain claimed.
