# ARVEXQ v3 phase 8 — per-circuit result & payout fact separation

Implementation in this **draft development PR**, NOT in main or deployed API:

- Central (JRA) and regional (NAR) each receive twelve physically separate,
  independently importable observed-only result field readers:
  4 finisher facts (rank, margin, clock, corners), 8 explicit payout kinds
  (単勝 / 複勝 / 枠連 / 馬連 / ワイド / 馬単 / 3連複 / 3連単).
- `result_facts.py` is the shared strict observed-data contract; individual
  field modules own a single extract. No alternate collection route exists.
- `result_split.py` composes only the existing saved result, preserves
  unknown payout kinds for diagnostics rather than deleting/reclassifying them.
  No inferred payout from odds or inferred finish from runner array order.
- `factual_response` and `factual_screen` expose `resultFields` ONLY for
  explicit `include_results=True` postrace access; prerelease results,
  postrace labels, predictions, marks and tickets are not exposed by default.
  No published HTTP endpoint or existing UI layout changed.
- A source result is `observed-unverified`; the module **does not** certify
  official result finality and does not write back corrected/final values.
  Existing archived original snapshots, D1, SQLite and seal records untouched.

### Coverage and limitations

The original independence ledger's #70-83 includes result/payout fields;
this stage implements field-level **read-only separation**, not complete
collector ownership, all source inputs, D1 roundtrip, live API release, or
production verification. Ledger statuses should not be promoted to
"completed" on this draft alone. Items #74, #84-86 (速報/補修/上書き防止)
remain to be independently implemented and verified.

Prediction architecture remains JRA/NAR × six empty units.
