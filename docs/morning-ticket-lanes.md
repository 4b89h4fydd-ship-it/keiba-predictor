# ARVEXQ X free morning race categorization

## Independent classifier
`arvexq/ui/static/morning/ticket_lane_classifier.js` is separate from the monolithic app and loaded independently by browser and morning capture.

- **的中重視型:** stable second/third role distributions and ◎ in leading place candidates; suitable for checking wide/quinella/trio, without requiring 1st-place gap.
- **勝ち馬明確型:** clear, stable winner and scenario, or the original strict selection gate; check exacta/trifecta.
- **高配当狙い型:** justified ☆ / ☆+ in the conditional second/third group; high payout is not guaranteed. 3連単 can still be skipped by the buying gate.
- Common safeguards: five or more runners, known pre-off readiness and coverage, quality evidence, axis, and explicit gate. No fixed daily maximum.
- Labels/selection reasons are published exactly once in `morning-picks/YYYY-MM-DD.json`, never reclassified after odds or results. Previously published dates are NOT backfilled; they display "厳選・旧方式".
- Type and 0–100 internal quality score are not measured accuracy or expected profit. Existing buy/no-buy logic remains authoritative.
- Morning membership is not updated later; special and selected races both read the immutable manifest.

## Actual ticket confirmation (new morning captures only)
After the three independent lane tests, the morning runner now runs the same
`buildAiBetPlan()` as the web app, with the separately loaded betting modules.
Public `selected` requires a non-skipped, input-ready 本線 / 保険 /
3連単チャレンジ ticket with valid runner numbers. A 3連単 alone must contain
6–12 combinations. Qualifying ticket kinds are written into
`selectionReason`. A high-scoring prediction with every ticket skipped is
**not** a public free selected race. The dated archive continues to be
first-write-wins: past dates are never retroactively changed. If the morning
inputs cannot pass the existing strict purchase-readiness checks, zero public
selected races is the safe and intentional result, not a license to fabricate
a ticket or loosen risk safeguards.

## Place-type bridge and archival
`的中重視型` can qualify without a dominant winner; its morning-specific
quality audit enters the real independent buying engine. The input-readiness,
ticket-concentration and 3連単 6–12 point gates still apply.
This lane can be recovered later pre-off only from a saved immutable archive.
`ticketKinds` is preserved in archives and summary metadata, while the
selection reason names the actual kinds that passed in the morning.

## Historical visibility / first-write-wins
The 2026-10-09 morning manifest has an old-method selected race 大井2R,
but it lacks type and actionable morning ticket evidence. The public
厳選 count excludes legacy/unverified picks. They remain inspectable in a
separate historical area and their JSON archive is not rewritten. New
frozen selections require type-matching saved ticketKinds. The iOS app
asset URL and one-time PWA reset token use v353 to prevent stale JS.

## v354: moderately wider criteria, and actionable no-◎ policy
Morning place selection can qualify on strong P2/P3 role concentration without an ◎; winner-clear and high-payout types continue to require ◎. Thresholds were only slightly eased. Independent no_axis_strategy.js considers ワイド, 馬連 or 3連複, never an ordered 1st-fixed ticket, and keeps existing purchase input-quality gates. A limited short-history exception to ◎ still requires much stronger independent evidence. Changes apply to new classifications, not retroactively to frozen predictions; official race-condition amendments use separate pre-off revision records, with reason and timestamp, preserving the original.
