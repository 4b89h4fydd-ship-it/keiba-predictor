# 未割当・空箱・共通所属の保留

新規処理を作って埋めない。元ソースはすべて保持する。

## 未割当の箱と互換のみの箱

| 番号 | 役割 | 状態 |
| --- | --- | --- |
| 112 | 予想ロジック | 互換用の空実装のみ |
| 114 | 展開シミュレーション | 未割当・空箱 |
| 116 | 印生成 | 互換用の空実装のみ |
| 117 | ◎【単】判定 | 未割当・空箱 |
| 118 | ◎【軸】判定 | 未割当・空箱 |
| 119 | その他の印判定 | 未割当・空箱 |
| 120 | A・B・C評価 | 未割当・空箱 |

5箱には研究候補の関連箇所を参照として保存している。未承認・撤去対象候補を現行経路へ戻さない。112/116は空の互換実装があるためソースの対応付けには含め、処理の存在件数193には含めない。

## 所属が確定しないファイル

以下78ファイルは無理に200箱へ割り振らず、原位置と依存を保存した。詳細な未割当定義1,112件、古いPR参照が最新mainにないケース、空箱の研究参照はunassigned-and-gaps.json.gzに記録。

| 原位置 | 静的app依存に存在 | 静的workflow依存に存在 |
| --- | --- | --- |
| arvexq/__init__.py | 未検出 | 未検出 |
| arvexq/backtest/audit_research_capture.py | 未検出 | 未検出 |
| arvexq/backtest/expected_value.py | 未検出 | 未検出 |
| arvexq/backtest/freeze_research_candidate.py | 未検出 | 有 |
| arvexq/backtest/frozen_research_tickets.py | 未検出 | 未検出 |
| arvexq/backtest/join_research_results.py | 未検出 | 未検出 |
| arvexq/backtest/metrics.py | 未検出 | 未検出 |
| arvexq/backtest/verify_research_receipt.py | 未検出 | 未検出 |
| arvexq/betting/scenario_tickets.py | 未検出 | 有 |
| arvexq/betting/trifecta.py | 未検出 | 未検出 |
| arvexq/config/settings.py | 未検出 | 未検出 |
| arvexq/core/__init__.py | 未検出 | 未検出 |
| arvexq/databanks/__init__.py | 未検出 | 有 |
| arvexq/forecast/__init__.py | 未検出 | 未検出 |
| arvexq/forecast/frozen_pace_context.py | 未検出 | 未検出 |
| arvexq/forecast/frozen_research_input.py | 未検出 | 未検出 |
| arvexq/forecast/race_softmax_research.py | 未検出 | 未検出 |
| arvexq/ingest/entry_fields/__init__.py | 未検出 | 未検出 |
| arvexq/ingest/odds_fields/__init__.py | 未検出 | 未検出 |
| arvexq/ingest/past_fields/__init__.py | 未検出 | 未検出 |
| arvexq/ingest/race_fields/__init__.py | 未検出 | 未検出 |
| arvexq/ingest/result_status/__init__.py | 未検出 | 未検出 |
| arvexq/pipeline/__init__.py | 未検出 | 未検出 |
| arvexq/prediction/__init__.py | 未検出 | 有 |
| arvexq/prediction/learned_scenarios.py | 未検出 | 有 |
| arvexq/prediction/mass_feature_factory.py | 有 | 有 |
| arvexq/prediction/mass_feature_selection.py | 有 | 有 |
| arvexq/prediction/mass_feature_snapshot.py | 有 | 有 |
| arvexq/prediction/mass_model_export.py | 未検出 | 未検出 |
| arvexq/prediction/mass_model_runtime.py | 未検出 | 未検出 |
| arvexq/prediction/mass_model_training.py | 未検出 | 未検出 |
| arvexq/prediction/mass_training_dataset.py | 未検出 | 未検出 |
| arvexq/prediction/mass_training_store.py | 未検出 | 未検出 |
| arvexq/prediction/new_forecast.py | 未検出 | 有 |
| arvexq/prediction/official_course_revision.py | 有 | 有 |
| arvexq/prediction/race_intelligence.py | 未検出 | 有 |
| arvexq/prediction/recommendation_engine.py | 未検出 | 未検出 |
| arvexq/prediction/special_marks.py | 未検出 | 未検出 |
| arvexq/prediction/user_approved_model_revision.py | 有 | 有 |
| arvexq/quality/__init__.py | 未検出 | 未検出 |
| arvexq/research/__init__.py | 未検出 | 未検出 |
| arvexq/research/margin_abcde_candidate.py | 有 | 有 |
| arvexq/research/preoff_coverage_audit.py | 未検出 | 有 |
| arvexq/results/__init__.py | 未検出 | 有 |
| arvexq/selection/race_selectability.py | 有 | 有 |
| arvexq/selection/race_selectability_snapshot.py | 有 | 有 |
| arvexq/selection/race_selectability_training.py | 未検出 | 有 |
| arvexq/selection/race_selector.py | 未検出 | 未検出 |
| arvexq/services/__init__.py | 有 | 有 |
| backtest_v206.py | 未検出 | 未検出 |
| backtest_v208_jra.py | 未検出 | 未検出 |
| scripts/arvexq_apply_learned_overlay.py | 未検出 | 有 |
| scripts/arvexq_apply_signal_dedup.py | 未検出 | 未検出 |
| scripts/arvexq_capture_batch_research.py | 未検出 | 有 |
| scripts/arvexq_capture_course_revised_marks.js | 未検出 | 有 |
| scripts/arvexq_capture_preoff_research.py | 未検出 | 未検出 |
| scripts/arvexq_collect_preoff_evidence.py | 未検出 | 未検出 |
| scripts/arvexq_collect_provisional_preoff.py | 未検出 | 有 |
| scripts/arvexq_empirical_ticket_calibration.py | 未検出 | 有 |
| scripts/arvexq_extract_backend.py | 未検出 | 未検出 |
| scripts/arvexq_extract_ui.py | 未検出 | 未検出 |
| scripts/arvexq_frozen_research_ticket_evaluation.py | 未検出 | 未検出 |
| scripts/arvexq_history_dedupe_challenger.py | 未検出 | 有 |
| scripts/arvexq_integrated_research.py | 未検出 | 未検出 |
| scripts/arvexq_learned_scenario_evaluation.py | 未検出 | 未検出 |
| scripts/arvexq_morning_picks.js | 未検出 | 有 |
| scripts/arvexq_rebuild_saved_forecasts.py | 未検出 | 有 |
| scripts/arvexq_remove_value_races.py | 未検出 | 未検出 |
| scripts/arvexq_selectability_audit.py | 未検出 | 有 |
| scripts/arvexq_special_forecast_ui.py | 未検出 | 未検出 |
| scripts/arvexq_train_research_models.py | 未検出 | 有 |
| scripts/arvexq_wire_core_marks.py | 未検出 | 未検出 |
| scripts/check_mass_feature_leakage.py | 未検出 | 未検出 |
| scripts/check_mass_training_store.py | 未検出 | 未検出 |
| scripts/check_prediction_app_integrity.py | 未検出 | 未検出 |
| scripts/check_race_selectability_snapshot.py | 未検出 | 有 |
| scripts/export_mass_training_dataset.py | 未検出 | 未検出 |
| scripts/train_mass_models.py | 未検出 | 未検出 |

「未検出」は未使用の証明ではない。動的参照・未追跡のコマンド文字列等を含め、稼働状態の推測はしない。
