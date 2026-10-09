# ARVEXQ dated five-run evidence and ◎

## Pre-off contract

The independently loaded Python module `arvexq/prediction/past_performance.py`
and browser module `betting/podium_axis_guard.js` consume only the five most
recent, verifiably dated starts strictly before the race date. Multiple source
lists are de-duplicated by race/date identity and sorted before truncation. A
missing date produces *unknown*, never zero talent or a fabricated result.
Cancelled or unknown-finish starts are not valid form observations.

## Diagnostic dimensions

- Five-run recency-weighted finish quality using prior field size, not raw
  finish rank alone.
- Same surface and +/-150m distance: observed finishes and podium count. If
  a candidate has repeated comparable starts and none made the podium, the
  `matchingConditionEvidence` axis check fails.
- Early passing position relative to field size and actual finishing
  position: repeated early pace followed by poor results is a fragility flag.
- Recent two-vs-older-three podium deterioration is another explicit flag.
- Course, going, numeric opponent-level, beaten margin, and observed final
  sectional *rank* are surfaced as diagnostics where present. Raw 3F clocks
  across incomparable tracks/distances are deliberately not used to award ◎.

Missing opposite-class, missing time or missing sectional rank is not
silently replaced by a score. Relative metrics are not calibrated win/podium
probabilities. Evidence families remain collapsed so a race's finish and
recent form do not become independent duplicate votes.

## Selection and publication

A new ◎ requires dated runs, a repeated top-three finish, compatible-history
evidence where at least two comparable starts exist, no repeated early fade,
no material recent downturn, a sufficiently distinct axis score, and
independent winner-head confirmation. Server and browser both withhold unsupported
◎. Without ◎, reference wide/quinella/trio choices may still be evaluated
separately. Existing immutable morning marks and pre-off tickets are never
recomputed, revised by history updates, or backfilled after the race.

The thresholds are provisional hypothesis checks. An improvement in hit rate
or ROI cannot be claimed until subsequent genuinely frozen samples and their
official results support it.
