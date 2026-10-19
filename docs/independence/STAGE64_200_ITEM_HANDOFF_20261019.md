# ARVEXQ 200-item separation: stage-64 handoff / evidence checkpoint (2026-10-19)

## Source of truth
- Fixed inventory: `docs/independence/requirements.json` (version 2, IDs 1..200).
- Branch: `feature/arvexq-v3-data-boundary-empty-prediction-20261019`; PR #367 stays DRAFT.
- Pre-audit head: `a4f64300b5fd5fe46e97aa6118a749c9cdaf83cd`.
- The archive/research stage-64 implementation is NOT a claim that the 200 production responsibilities are all separated.

## Snapshot (from the actual inventory)
| Source status | Items | Reporting classification |
| --- | ---: | --- |
| 本番検証済 | 3 | Ledger-certified only; requires renewed ten-gate review |
| main統合済 | 3 | Partial |
| 分離済 | 8 | Partial |
| 解析済 | 61 | Partial |
| 未着手 | 96 | Not started |
| 予想ロジック仕様待ち | 29 | Not started / approval-blocked |
| **Total** | **200** | **3 ledger-certified, 72 partial, 125 not started or waiting** |

All 200 inventory IDs and referenced implementation/test paths were located in the stage-64 branch tree at the checkpoint. **Path existence is not test success.** The existing `arvexq_independence_audit.py` validates evidence receipt presence and previous production status; it does not independently prove the ten per-item gates.

## Required ten gates per responsibility
1. Acquisition: existing source, owner and source boundaries established.
2. Normalization: verified valid/null/invalid behavior without fabricated values.
3. Persistence: schema/owner/readback confirmed without deleting or rewriting historic records.
4. Cache: circuit-specific identities, freshness and invalidation verified.
5. API: factual DTO, circuit isolation and leakage protection verified.
6. UI: existing view contract and missing-state rendering verified without design changes.
7. Circuit separation: JRA/NAR positive and opposite-circuit refusal tests.
8. Dependencies: caller graph and any shared code owner explicitly recorded.
9. Missing/abnormal data: non-fabrication, duplicate, invalid and temporal edge-case tests.
10. Tests/results: precise test identifier, passing commit and CI URL; production readback when relevant.

Per-item outcome must be one of 完了, 部分完了, 未着手, 要修正, 確認不能. Only promote to 完了 after applicable ten-gate evidence and required production readback; no batch CI pass is a shortcut.

## Next batch: IDs 004–020 (17 JRA race/environment items)
- Confirm actual call sites and source-specific ownership for IDs 004–020 before changing any extractor.
- Map each of the ten gates to file/test/CI evidence; label missing gates explicitly.
- Add focused read-only mismatch, missingness, JRA/NAR cross-circuit and regression tests where the existing implementation does not establish independence.
- Preserve existing provider registry, persisted originals, storage, UI, deployed Worker and all 12 empty v3 prediction components.
- Do not deploy or merge. In particular, do not dispatch the production deployment command proposed by the historical item-002 progress note.

## Existing blockers / research boundary
- Historical item-002 progress note is older than the manifest's more recent GET-only readback record. Do not roll back its ledger status solely because the old note is stale; verify evidence dates before changing status.
- Live JRA/NAR full population readback, all historical source routes, cache and UI interactions are not certified by existence of v3 reader modules.
- Stage64 historical 527-race replay is not independent prospective evaluation; no 80%-90% hit-rate or sustained 100% return has been demonstrated.
- Prediction logic, marks and recommended tickets remain approval-gated and must not be connected to production.

## Reproduction / handoff
```bash
python scripts/arvexq_independence_audit.py
python -m pytest -q tests/test_independence_evidence.py
python -m pytest -q tests/test_environment_component_split.py tests/test_independent_jra_race_identity.py tests/test_jra_race_fields_independent.py
```
Review the actual GitHub Actions checks for the HEAD commit and resume with items 004–020. Append dated evidence to this checkpoint rather than replacing original observations. The main branch and all production surfaces remain out of scope.

## Batch 004–020 checkpoint (sub-batch 004–007)
- Scope audited in code: `jra_environment_parser.py` composing `jra_weather.py`, `jra_turf_going.py`, `jra_dirt_going.py`, and `jra_obstacle_going.py`.
- Added four read-only regression cases to `tests/test_environment_component_split.py`: missing NAR-only 馬場状態 is not repurposed as JRA going, turf/dirt selected condition does not cross-assign, missing obstacle conditions remain missing, and obstacle projection does not mutate supplied field observations.
- These are focused unit/integration-level contracts only. No independent complete acquisition/storage/cache/API/UI/production gates yet. Items 004–007 remain **部分完了**, recorded source statuses `分離済` unchanged.
- Items 008–020 remain `解析済` with future extraction/caller audits outstanding.
- CI must be inspected on the new HEAD before calling these tests passed. No provider changes, prediction implementation, deploy or main merge.

## 2026-10-19 continuation: 004–007 connection-path repair

- Audited the two remaining JRA race-card callers: `_jra_parse_race` and `_jra_parse_race_summary`.
- Removed their duplicate weather/going regular expressions and routed both through `arvexq.ingest.jra_environment_parser._parse_jra_environment_html`, preserving the existing `weather`/`condition` output keys and unknown-value behavior.
- Added a fail-closed ownership guard in `_jra_fetch_environment`: an explicitly identified `nar-...` row is not sent to the JRA reader and performs no request.
- Added source-contract and cross-circuit regression tests in `tests/test_jra_summary_independent_fields.py` and `tests/test_environment_component_split.py`.
- Code/test commit: `8c2b94b56fb93f69093db7a8ec567e19143bfb3a`.
- Local `compileall` and `arvexq_independence_audit.py` passed. Local pytest/app-import execution remains unverified because this workspace lacks `pytest` and `bs4`; CI on the pushed commit is required before recording test success.
- Items 004–007 remain **部分完了** / source status `分離済`; this repair does not promote any ledger item.

### CI confirmation for repaired HEAD

All six PR workflows completed successfully for `597270d74e7f3bb7f4c1cc6e31b4c3241d7c3582`:

`ARVEXQ Environment Modules` **39273981088**, `ARVEXQ Factual Data Audit` **39273981134**, `ARVEXQ Stage64 Shadow Research` **39273981137**, `ARVEXQ Independent Components` **39273981253**, `ARVEXQ v3 Saved-Archive Audit` **39273981249**, and `ARVEXQ Validation` **39273981299**. This establishes CI success for the changed contracts only; it does not satisfy persistence/cache/API/UI/production gates or promote 004–007.

Local dependency-isolated rerun of the 008–020 field, v3 transport, circuit-separation, FastAPI saved-read, and ledger tests: **81 passed**. No ledger status was promoted; production readback remains unverified.
