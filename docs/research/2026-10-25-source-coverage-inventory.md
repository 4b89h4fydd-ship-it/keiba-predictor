# Source coverage audit: JRA debut and jumps (2026-10-25)

Scope: Read existing providers and fill only verified bloodlines. Central and regional circuits remain separate. No changes to winning probabilities, marks, tickets, or production deployment.

MotherDuck evidence: 401 races saved (last race date 2026-10-21). JRA debut 10 races / 127 runners; JRA jumps 2 races / 17 runners. All 12 have empty pedigree provider lists, no observed sire/dam/damsire in the compact runner rows, and no first-runner JRA profile identity in the persisted JSON. These facts do NOT establish that upstream sources have no pedigree.

Existing data sources:
- JRA official race detail / result / career already registered. The official horse profile has sire/dam/damsire; register a pedigree capability on the existing profile URL, requiring an observed JRA horse CNAME. Do not guess identity when absent.
- SmartRc: existing configured-feed pathway only. Decode lineage attributes when the feed is configured; do not reactivate retired tempo/final-section indicators.
- Netkeiba: existing career, result and odds providers, but no currently registered pedigree provider. No verified claim that a bloodline was fetched from this service.
- JBIS: source builder and catalog entry exist but no active provider in the legacy source registry. Contract and machine-access method not verified.
- JRA-VAN/JV-Link/JRDB: external data products exist; no verified ARVEXQ-accessible entitlement, account, or commercial reuse permission.
- Supplemental extra feeds: consume only if existing configuration is present. Configuration has not been independently verified.
- Local NAR official / CSV: preserve separately, never fill JRA jump ability from flat/NAR scores.

Known blockers for real historic backfill: stored race details do not retain first-runner horse profile CNAME; live feed authentication/configuration unconfirmed; no new preoff originals exist for earlier outcomes. Unit/CI success is NOT live JRA retrieval success.

Required end-to-end verification: acquire actual dated upstream record, attach source and acquisition time, store and read back D1, measure completeness by race type, keep immutable preoff forecast, then compare against official outcome without leakage.