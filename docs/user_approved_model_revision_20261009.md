# User-approved immediate past-five model application (2026-10-09)

An explicit user request on October 9 authorized applying the improved past-five
horse-racing mark model immediately. It did **not** authorize re-editing races
whose scheduled start had passed, or silently rewriting a morning original.

## Policy

- First-write morning marks remain in `morningMarkSnapshot`; the original
  `morning-picks/YYYY-MM-DD.json` race selection and the separate locked
  ticket are never modified.
- A one-time `user-approved-past-five-from-2026-10-09-20-10-jst` event can
  create `modelMarkRevisions` ONLY for races dated October 9 that are not
  yet started, have an original morning mark snapshot, and do not have a
  sealed forecast or an original captured bet.
- The revision includes exact approval ID, model version, calculation
  timestamp, changed horse numbers and reason, and carries its own provenance:
  *explicit-user-request*. It does **not** claim that an official racecourse
  published a track bias update.
- Both the browser and the pre-off prediction sealing logic select the most
  recent valid official revision or approved model revision by actual pre-off
  timestamp. Unverified or post-off records are discarded.
- `arvexq_protect_sync.py` only accepts a valid, timely append from the
  explicit user-approval flow and never overwrites earlier history.
- The model switch is already part of the next racing morning. No artificial
  history is backfilled if there were no eligible races remaining at the
  deployment time.

## Verification

`tests/test_user_approved_model_revision.py` validates approval provenance,
time windows, unchanged morning original, preserved tickets, rejection of
forged and post-off candidates, and idempotence. Browser selection and
precedence are verified by `scripts/arvexq_model_mark_revision_smoke.js`.
The GitHub Actions live sync is triggered by changes to the model revision
module and runs only if actual racing day data exists.

A successful CI run establishes correctness of the guard logic, **not** that
a mark was modified in production. A production update must be corroborated
by a `USER_APPROVED_MODEL_MARK_REVISION` audit record and D1 readback.
