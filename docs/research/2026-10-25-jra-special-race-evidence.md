# JRA specialist evidence audit — 2026-10-25

New race-detail evidence namespaces: `jra-debut` and `jra-jumps`, attached through the existing read-only decoration path. They do not calculate marks, odds, tickets, or probabilities, and do not read post-race results.

Historical MotherDuck snapshot inventory: 401 race details dated 2026-10-15 to 2026-10-21, including 72 JRA races. Of these, 10 debut races (127 horses) and 2 jump races (17 horses) are recognized. No original pre-race predictions or pre-race tickets were found in those saved snapshots.

Data gaps in the top-level compact horse records: no sire or dam fields in the 127 debut runners; no jumpStats in the 17 jump runners. Packed history fields are not evidence that a runner has no race history.

Debut evidence to acquire via the existing official provider path: pedigree, historical sire/trainer/jockey debut performance, observed training times, gate exams and source timestamps.

Jump evidence to acquire: independently identified past jump starts, jump exams, race-specific course/obstacle characteristics, measured jump consistency, rider history and official course records. Flat form remains supporting context, not a substitute for jump record.

JRA sources:
- https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0105202604090520261025%2FDD
- https://www.jra.go.jp/keiba/race/096.html
- https://www.jra.go.jp/keiba/thisweek/2026/0516_1/horse.html

Do not claim prediction performance until separately sealed pre-off forecasts, full official results and actual frozen tickets exist. The specialist boxes are data-management annotations only, not validated prediction models.
