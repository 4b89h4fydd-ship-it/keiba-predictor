# ARVEXQ 第6段階 178項目別コード照合と検証範囲

対象：PR #386、source inspection基点 `4ba9a461f166b711edc2e67c3c8babed5edd884a`、178項目pytest基点 `d5b5e426ca79218e65e1ef6a384fd6f7563de566`。未接続22項目を変更せず、項目別接続record 723（共有重複を除くと625）。呼び出し元・箱・元実装の**実ファイル存在178/178**、全件ソースを読むStage6 pytest **178/178 pass**。Stage4の旧176項目は過去の境界検証 `pass` 記録あり。160・175は第5/6段階の専用オフラインテストを実施。

**注意：全データ・全分岐・本番動作の178件成功認定ではない。** 全項目の完全実行認定は0件。部分保留15件は保持。第6段階追加テストは構文、パス、シンボル、既存転送構造、Python箱間の静的循環を検査。コードを読む静的検査と実際の予想結果/本番検証を混同しない。詳細は `item-results.json`。

| # | 項目 | 系統 | 接続record | caller（既存入口） | 箱（接続先） | 元実装 | 検査 / 残課題 |
|---:|---|---|---:|---|---|---|---|
| 001 | NAR天候解析 | NAR | 10 | `app.py`, `arvexq/ingest/jra_dirt_going.py`, `arvexq/ingest/jra_turf_going.py` 他4 | `arvexq/components/item_001/environment_values.py`, `arvexq/components/item_001/nar_weather.py` | `arvexq/ingest/environment_values.py`, `arvexq/ingest/nar_weather.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 002 | NAR馬場状態解析 | NAR | 3 | `app.py`, `arvexq/ingest/nar_environment_parser.py` | `arvexq/components/item_002/nar_environment_parser.py`, `arvexq/components/item_002/nar_going.py` | `arvexq/ingest/nar_environment_parser.py`, `arvexq/ingest/nar_going.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 003 | NAR出走取消・除外解析 | NAR | 1 | `arvexq/ingest/nar_environment_parser.py` | `arvexq/components/item_003/nar_scratches.py` | `arvexq/ingest/nar_scratches.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 004 | JRA天候解析 | JRA | 1 | `arvexq/ingest/jra_environment_parser.py` | `arvexq/components/item_004/jra_weather.py` | `arvexq/ingest/jra_weather.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 005 | JRA芝馬場状態解析 | JRA | 1 | `arvexq/ingest/jra_environment_parser.py` | `arvexq/components/item_005/jra_turf_going.py` | `arvexq/ingest/jra_turf_going.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 006 | JRAダート馬場状態解析 | JRA | 1 | `arvexq/ingest/jra_environment_parser.py` | `arvexq/components/item_006/jra_dirt_going.py` | `arvexq/ingest/jra_dirt_going.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 007 | JRA障害コース馬場状態判定 | JRA | 1 | `arvexq/ingest/jra_environment_parser.py` | `arvexq/components/item_007/jra_obstacle_going.py` | `arvexq/ingest/jra_obstacle_going.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 008 | 開催日取得 | JRA | 2 | `app.py` | `arvexq/components/item_008/jra_identifiers.py`, `arvexq/components/item_008/routes.py` | `arvexq/ingest/jra_identifiers.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 009 | 開催場取得 | JRA | 2 | `app.py` | `arvexq/components/item_009/track.py`, `arvexq/components/item_009/routes.py` | `arvexq/ingest/race_fields/track.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 010 | 開催日程取得 | JRA | 3 | `app.py` | `arvexq/components/item_010/meeting_schedule.py`, `arvexq/components/item_010/routes.py` | `arvexq/ingest/race_fields/meeting_schedule.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 011 | レース番号取得 | JRA | 1 | `app.py` | `arvexq/components/item_011/jra_identifiers.py` | `arvexq/ingest/jra_identifiers.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 012 | レース名取得 | JRA | 1 | `app.py` | `arvexq/components/item_012/title.py` | `arvexq/ingest/race_fields/title.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 013 | グレード・クラス取得 | JRA | 1 | `app.py` | `arvexq/components/item_013/grade_class.py` | `arvexq/ingest/race_fields/grade_class.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 014 | 発走時刻取得 | JRA | 3 | `app.py` | `arvexq/components/item_014/jra_time.py`, `arvexq/components/item_014/start_time.py` | `arvexq/ingest/jra_time.py`, `arvexq/ingest/race_fields/start_time.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 015 | 芝・ダート・障害区分取得 | JRA | 1 | `app.py` | `arvexq/components/item_015/surface.py` | `arvexq/ingest/race_fields/surface.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 016 | 距離取得 | JRA | 1 | `app.py` | `arvexq/components/item_016/distance.py` | `arvexq/ingest/race_fields/distance.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 017 | コース情報取得 | JRA | 4 | `app.py`, `arvexq/ingest/race_fields/distance.py`, `arvexq/ingest/race_fields/surface.py` 他1 | `arvexq/components/item_017/course.py`, `arvexq/components/item_017/race_conditions.py` | `arvexq/ingest/race_fields/course.py`, `arvexq/race_conditions.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 018 | 出走頭数取得 | JRA | 1 | `app.py` | `arvexq/components/item_018/field_size.py` | `arvexq/ingest/race_fields/field_size.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 019 | 賞金情報取得 | JRA | 1 | `app.py` | `arvexq/components/item_019/prize.py` | `arvexq/ingest/race_fields/prize.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 020 | JRA公式データ解析 | JRA | 18 | `app.py`, `arvexq/ingest/nar_csv.py` | `arvexq/components/item_020/pure_parsers.py`, `arvexq/components/item_020/routes.py` | `arvexq/ingest/pure_parsers.py`, `app.py` | 静的照合pass / Stage4境界pass / 部分保留2 / 全分岐・本番未認定 |
| 021 | NAR公式データ解析 | NAR | 8 | `app.py`, `scripts/arvexq_nar_csv_coverage.py` | `arvexq/components/item_021/nar_csv.py`, `arvexq/components/item_021/nar_official_metadata.py`, `arvexq/components/item_021/routes.py` | `arvexq/ingest/nar_csv.py`, `arvexq/ingest/nar_official_metadata.py`, `app.py` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 022 | 外部競馬サイトデータ解析 | JRA+NAR | 8 | `app.py` | `arvexq/components/item_022/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 部分保留6 / 全分岐・本番未認定 |
| 023 | レースID照合 | JRA+NAR | 2 | `arvexq/ingest/nar_csv.py` | `arvexq/components/item_023/race_identity.py` | `arvexq/ingest/race_identity.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 024 | 重複レース統合 | JRA+NAR | 3 | `app.py` | `arvexq/components/item_024/race_summary_merge.py` | `arvexq/ingest/race_summary_merge.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 025 | 馬番 | JRA+NAR | 3 | `app.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_025/horse_number.py`, `arvexq/components/item_025/routes.py`, `arvexq/components/item_025/module_reference_horse_number.py` | `arvexq/ingest/entry_fields/horse_number.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 026 | 枠番 | JRA+NAR | 3 | `app.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_026/frame_number.py`, `arvexq/components/item_026/netkeiba.py`, `arvexq/components/item_026/module_reference_frame_number.py` | `arvexq/ingest/entry_fields/frame_number.py`, `arvexq/ingest/entry_fields/netkeiba.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 027 | 馬名 | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_027/module_reference_name.py` | `arvexq/ingest/entry_fields/name.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 028 | 性別 | JRA+NAR | 2 | `arvexq/ingest/field_normalization.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_028/sex.py`, `arvexq/components/item_028/module_reference_sex.py` | `arvexq/ingest/entry_fields/sex.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 029 | 年齢 | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_029/module_reference_age.py` | `arvexq/ingest/entry_fields/age.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 030 | 斤量 | JRA+NAR | 2 | `arvexq/ingest/horse_measurements.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_030/carried_weight.py`, `arvexq/components/item_030/module_reference_carried_weight.py` | `arvexq/ingest/entry_fields/carried_weight.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 031 | 騎手 | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_031/module_reference_jockey.py` | `arvexq/ingest/entry_fields/jockey.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 032 | 調教師 | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_032/module_reference_trainer.py` | `arvexq/ingest/entry_fields/trainer.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 033 | 所属 | JRA+NAR | 2 | `app.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_033/affiliation.py`, `arvexq/components/item_033/module_reference_affiliation.py` | `arvexq/ingest/entry_fields/affiliation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 034 | 馬体重 | JRA+NAR | 5 | `app.py`, `arvexq/ingest/horse_measurements.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_034/horse_measurements.py`, `arvexq/components/item_034/body_weight.py`, `arvexq/components/item_034/module_reference_body_weight.py` | `arvexq/ingest/horse_measurements.py`, `arvexq/ingest/entry_fields/body_weight.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 035 | 馬体重増減 | JRA+NAR | 2 | `arvexq/ingest/horse_measurements.py`, `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_035/body_weight_change.py`, `arvexq/components/item_035/module_reference_body_weight_change.py` | `arvexq/ingest/entry_fields/body_weight_change.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 036 | 出走取消状態 | JRA+NAR | 27 | `app.py`, `arvexq/betting/scenario_tickets.py`, `arvexq/features/horse_features.py` 他13 | `arvexq/components/item_040/field_normalization.py`, `arvexq/components/item_036/runner_status.py`, `arvexq/components/item_036/runner_cancellation.py` | `arvexq/ingest/field_normalization.py`, `arvexq/core/runner_status.py`, `arvexq/ingest/runner_cancellation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 037 | 競走除外状態 | JRA+NAR | 24 | `app.py`, `arvexq/ingest/corner_order.py`, `arvexq/ingest/entry_fields/dom.py` 他10 | `arvexq/components/item_040/field_normalization.py`, `arvexq/components/item_037/runner_exclusion.py` | `arvexq/ingest/field_normalization.py`, `arvexq/ingest/runner_exclusion.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 038 | 出馬表更新 | JRA+NAR | 6 | `app.py` | `arvexq/components/item_038/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 039 | 馬名・馬番照合 | JRA+NAR | 3 | `app.py`, `arvexq/ingest/source_merge.py` | `arvexq/components/item_039/horse_identity.py`, `arvexq/components/item_039/merge.py` | `arvexq/ingest/horse_identity.py`, `arvexq/databanks/merge.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 040 | 欠損値補完 | JRA+NAR | 27 | `app.py`, `arvexq/ingest/corner_order.py`, `arvexq/ingest/entry_fields/dom.py` 他10 | `arvexq/components/item_040/field_normalization.py`, `arvexq/components/item_040/enrichment_transport.py`, `arvexq/components/item_040/source_merge.py` 他1 | `arvexq/ingest/field_normalization.py`, `arvexq/ingest/enrichment_transport.py`, `arvexq/ingest/source_merge.py` 他1 | 静的照合pass / Stage4境界pass / 部分保留3 / 全分岐・本番未認定 |
| 041 | データ取得元照合 | JRA+NAR | 17 | `arvexq/databanks/jbis.py`, `arvexq/databanks/jra.py`, `arvexq/databanks/nar.py` 他5 | `arvexq/components/item_041/registry.py`, `arvexq/components/item_041/orchestrator.py` | `arvexq/databanks/registry.py`, `arvexq/ingest/orchestrator.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 042 | 過去走日付 | JRA | 4 | `app.py`, `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_042/jra.py`, `arvexq/components/item_042/recent_result_cell.py`, `arvexq/components/item_042/date.py` 他1 | `arvexq/ingest/past_fields/jra.py`, `arvexq/ingest/recent_result_cell.py`, `arvexq/ingest/past_fields/date.py` 他1 | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 043 | 過去走競馬場 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_043/track.py` | `arvexq/ingest/past_fields/track.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 044 | 過去走距離 | JRA | 2 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_044/distance.py` | `arvexq/ingest/past_fields/distance.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 045 | 過去走馬場状態 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_045/going.py` | `arvexq/ingest/past_fields/going.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 046 | 過去走クラス | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_046/grade.py` | `arvexq/ingest/past_fields/grade.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 047 | 過去走着順 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_047/finish.py` | `arvexq/ingest/past_fields/finish.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 048 | 過去走走破時計 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_048/clock.py` | `arvexq/ingest/past_fields/clock.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 049 | 過去走着差 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_049/margin.py` | `arvexq/ingest/past_fields/margin.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 050 | 過去走通過順位 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_050/corners.py` | `arvexq/ingest/past_fields/corners.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 051 | 過去走上がり情報 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_051/last3f.py` | `arvexq/ingest/past_fields/last3f.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 052 | 過去走斤量 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_052/carried_weight.py` | `arvexq/ingest/past_fields/carried_weight.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 053 | 過去走騎手 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_053/jockey.py` | `arvexq/ingest/past_fields/jockey.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 054 | 過去走出走頭数 | JRA | 1 | `arvexq/ingest/past_fields/jra.py` | `arvexq/components/item_054/field_size.py` | `arvexq/ingest/past_fields/field_size.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 055 | 過去走重複排除 | JRA | 3 | `app.py`, `arvexq/ui/bundle.py` | `arvexq/components/item_055/routes.py`, `arvexq/components/item_055/assets.py` | `app.py`, `arvexq/ui/static/history/deduplicate.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 056 | JRA・NAR転入転出判別 | JRA+NAR | 1 | `arvexq/ingest/transfer_history.py` | `arvexq/components/item_056/circuit_transfer.py` | `arvexq/ingest/circuit_transfer.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 057 | 全競走履歴取得・補修 | JRA+NAR | 40 | `app.py`, `arvexq/career_missing.py`, `arvexq/horse_detail.py` 他11 | `arvexq/components/item_057/nar_career_coverage.py`, `arvexq/components/item_057/jra_career_merge.py`, `arvexq/components/item_057/career_analysis.py` 他4 | `arvexq/ingest/nar_career_coverage.py`, `arvexq/ingest/jra_career_merge.py`, `arvexq/career_analysis.py` 他4 | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 058 | 未来結果混入防止 | JRA+NAR | 1 | `arvexq/ui/bundle.py` | `arvexq/components/item_058/assets.py` | `arvexq/ui/static/history/temporal.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 059 | 単勝オッズ | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_059/module_reference_win_odds.py` | `arvexq/ingest/entry_fields/win_odds.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 060 | 複勝オッズ | JRA+NAR | 1 | `app.py` | `arvexq/components/item_060/place_odds.py` | `arvexq/ingest/place_odds.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 061 | 人気順位 | JRA+NAR | 1 | `arvexq/ingest/entry_fields/netkeiba.py` | `arvexq/components/item_061/module_reference_popularity.py` | `arvexq/ingest/entry_fields/popularity.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 062 | オッズ取得時刻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_062/odds_capture_time.py` | `arvexq/ingest/odds_capture_time.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 063 | JRAオッズ解析 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_063/netkeiba_odds_parser.py` | `arvexq/ingest/netkeiba_odds_parser.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 064 | NARオッズ解析 | NAR | 3 | `app.py` | `arvexq/components/item_064/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 065 | 外部サイトオッズ解析 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_065/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 066 | オッズ差分更新 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_066/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 067 | オッズ保存・復元 | JRA+NAR | 2 | `app.py`, `workers/web.mjs` | `arvexq/components/item_067/routes.py`, `arvexq/components/item_067/saved_odds.mjs` | `app.py`, `workers/saved_odds.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 068 | オッズ表示 | JRA+NAR | 5 | `arvexq/services/race_analysis.py`, `arvexq/ui/static/app.js` | `arvexq/components/item_068/odds.py`, `arvexq/components/item_068/routes.js` | `arvexq/odds.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 069 | オッズ欠損判定 | JRA+NAR | 2 | `app.py`, `arvexq/ingest/odds_fields/delta.py` | `arvexq/components/item_069/missing.py` | `arvexq/ingest/odds_fields/missing.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 073 | 確定結果判定 | JRA+NAR | 2 | `app.py`, `scripts/arvexq_verify_history_bundle.py` | `arvexq/components/item_073/confirmed.py`, `arvexq/components/item_073/state.py` | `arvexq/ingest/result_status/confirmed.py`, `arvexq/results/state.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 074 | 速報結果判定 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_073/confirmed.py` | `arvexq/ingest/result_status/confirmed.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 075 | コーナー通過順位取得 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_075/corner_order.py` | `arvexq/ingest/corner_order.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 076 | 単勝払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 077 | 複勝払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 078 | 枠連払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 079 | 馬連払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 080 | ワイド払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 081 | 馬単払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 082 | 3連複払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 083 | 3連単払戻 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_076/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 084 | 結果欠損補修 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_084/odds_results_merge.py` | `arvexq/ingest/odds_results_merge.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 085 | 払戻欠損補修 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_085/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 086 | 確定結果上書き防止 | JRA+NAR | 4 | `app.py` | `arvexq/components/item_086/pure_snapshots.py`, `arvexq/components/item_086/routes.py` | `arvexq/infra/pure_snapshots.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 087 | データ完全性評価 | JRA+NAR | 8 | `app.py` | `arvexq/components/item_087/pure_diagnostics.py`, `arvexq/components/item_087/routes.py` | `arvexq/prediction/pure_diagnostics.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 088 | 近走成績評価 | JRA+NAR | 5 | `arvexq/services/race_analysis.py`, `app.py` | `arvexq/components/item_088/horse_features.py`, `arvexq/components/item_088/routes.py` | `arvexq/features/horse_features.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 089 | 能力評価 | JRA+NAR | 4 | `arvexq/ability_engine.py`, `arvexq/services/race_analysis.py` | `arvexq/components/item_089/ability.py` | `arvexq/prediction/ability.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 090 | クラス適性 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_090/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 091 | 距離適性 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_090/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 092 | 競馬場適性 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_090/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 094 | 馬場適性 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_090/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 095 | 季節適性 | JRA+NAR | 3 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_090/routes.py`, `arvexq/components/item_095/pure_diagnostics.py` | `app.py`, `arvexq/prediction/pure_diagnostics.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 096 | 走破時計評価 | JRA+NAR | 3 | `arvexq/domain/legacy_evaluation.py`, `app.py` | `arvexq/components/item_096/routes.py`, `arvexq/components/item_096/pure_diagnostics.py` | `arvexq/domain/legacy_evaluation.py`, `arvexq/prediction/pure_diagnostics.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 097 | 上がり性能評価 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_097/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 098 | 逃げ率 | JRA+NAR | 4 | `arvexq/services/race_analysis.py`, `app.py` | `arvexq/components/item_105/pace_prediction.py`, `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `arvexq/pace_prediction.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 099 | 先行率 | JRA+NAR | 4 | `arvexq/services/race_analysis.py`, `app.py` | `arvexq/components/item_105/pace_prediction.py`, `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `arvexq/pace_prediction.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 100 | 差し率 | JRA+NAR | 4 | `arvexq/services/race_analysis.py`, `app.py` | `arvexq/components/item_105/pace_prediction.py`, `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `arvexq/pace_prediction.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 101 | 追込率 | JRA+NAR | 4 | `arvexq/services/race_analysis.py`, `app.py` | `arvexq/components/item_105/pace_prediction.py`, `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `arvexq/pace_prediction.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 102 | 下がり率 | JRA+NAR | 1 | `arvexq/services/race_analysis.py` | `arvexq/components/item_105/pace_prediction.py` | `arvexq/pace_prediction.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 103 | 脚質点 | JRA+NAR | 3 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 104 | 位置取り評価 | JRA+NAR | 3 | `app.py` | `arvexq/components/item_088/routes.py`, `arvexq/components/item_098/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 105 | 展開・ペース分析 | JRA+NAR | 1 | `arvexq/services/race_analysis.py` | `arvexq/components/item_105/pace_prediction.py` | `arvexq/pace_prediction.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 106 | 先行争い分析 | JRA+NAR | 1 | `arvexq/domain/legacy_evaluation.py` | `arvexq/components/item_106/routes.py` | `arvexq/domain/legacy_evaluation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 107 | 騎手・調教師情報評価 | JRA+NAR | 1 | `arvexq/domain/legacy_evaluation.py` | `arvexq/components/item_107/routes.py` | `arvexq/domain/legacy_evaluation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 108 | 馬体重・斤量影響分析 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_108/pure_diagnostics.py` | `arvexq/prediction/pure_diagnostics.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 109 | コース別スピード基準 | JRA+NAR | 6 | `app.py`, `arvexq/domain/legacy_evaluation.py` | `arvexq/components/item_109/course_speed_baselines.py`, `arvexq/components/item_096/routes.py` | `arvexq/prediction/course_speed_baselines.py`, `arvexq/domain/legacy_evaluation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 110 | 全頭診断結果保存・表示 | JRA+NAR | 11 | `app.py`, `arvexq/services/race_analysis.py`, `arvexq/domain/legacy_evaluation.py` | `arvexq/components/item_110/services_package.py`, `arvexq/components/item_110/diagnosis.py`, `arvexq/components/item_110/routes.py` 他1 | `arvexq/services/__init__.py`, `arvexq/diagnosis.py`, `app.py` 他1 | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 111 | 予想入力データ | JRA+NAR | 4 | `scripts/arvexq_history_repair.py`, `scripts/arvexq_select_prefetch_repairs.py`, `scripts/arvexq_verify_persisted_inputs.py` | `arvexq/components/item_111/fingerprints.py`, `arvexq/components/item_111/persisted_inputs.py` | `arvexq/pipeline/fingerprints.py`, `arvexq/pipeline/persisted_inputs.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 113 | 勝率・順位確率計算 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_113/pure_diagnostics.py` | `arvexq/prediction/pure_diagnostics.py` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 115 | 予想信頼度判定 | JRA+NAR | 1 | `arvexq/services/race_analysis.py` | `arvexq/components/item_115/confidence.py` | `arvexq/prediction/confidence.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 121 | 買い目生成 | JRA+NAR | 1 | `arvexq/ui/bundle.py` | `arvexq/components/item_121/assets.py` | `arvexq/ui/static/forecast/tickets.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 125 | 発走前の予想・買い目保存 | JRA+NAR | 8 | `arvexq/forecast/preoff_d1_transport.py`, `scripts/arvexq_collect_preoff_evidence.py`, `scripts/arvexq_verified_holdout.py` 他1 | `arvexq/components/item_125/preoff_evidence_store.py`, `arvexq/components/item_125/preoff_capture.py`, `arvexq/components/item_125/routes.js` | `arvexq/forecast/preoff_evidence_store.py`, `arvexq/forecast/preoff_capture.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 126 | 予想・印・買い目画面表示 | JRA+NAR | 2 | `arvexq/ui/bundle.py` | `arvexq/components/item_126/assets.py` | `arvexq/ui/static/forecast/prediction.js`, `arvexq/ui/static/forecast/marks.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 127 | 的中判定・成績検証 | JRA+NAR | 1 | `scripts/arvexq_daily_archive_audit.py` | `arvexq/components/item_127/auto_recap.py` | `arvexq/results/auto_recap.py` | 静的照合pass / Stage4境界pass / 部分保留2 / 全分岐・本番未認定 |
| 128 | 中央・地方開催区分 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_128/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 129 | 本日の厳選レース | JRA+NAR | 8 | `app.py`, `arvexq/domain/legacy_evaluation.py` | `arvexq/components/item_129/routes.py`, `arvexq/components/item_110/routes.py`, `arvexq/components/item_106/routes.py` | `app.py`, `arvexq/domain/legacy_evaluation.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 130 | メインレース | JRA+NAR | 2 | `arvexq/ui/static/app.js` | `arvexq/components/item_130/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 131 | 重賞レース | JRA+NAR | 1 | `arvexq/ui/static/app.js` | `arvexq/components/item_131/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 132 | 高知ファイナル | JRA+NAR | 1 | `arvexq/ui/static/app.js` | `arvexq/components/item_132/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 133 | レース選定条件 | JRA+NAR | 3 | `arvexq/ui/static/app.js` | `arvexq/components/item_133/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 136 | 厳選レース買い目表示 | JRA+NAR | 1 | `arvexq/ui/static/app.js` | `arvexq/components/item_136/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 138 | 当日予想成績 | JRA+NAR | 7 | `arvexq/ui/static/app.js` | `arvexq/components/item_138/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 139 | D1保存 | JRA+NAR | 2 | `workers/api.mjs` | `arvexq/components/item_139/api_full_snapshot.mjs` | `workers/api_full_snapshot.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 140 | SQLite保存 | JRA+NAR | 3 | `app.py` | `arvexq/components/item_140/race_stores.py`, `arvexq/components/item_140/routes.py` | `arvexq/infra/race_stores.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 141 | レース一覧キャッシュ | JRA+NAR | 14 | `app.py` | `arvexq/components/item_141/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 142 | レース詳細キャッシュ | JRA+NAR | 3 | `app.py` | `arvexq/components/item_142/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 145 | オッズキャッシュ | JRA+NAR | 1 | `workers/web.mjs` | `arvexq/components/item_173/web_entry.mjs` | `workers/web.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 146 | 結果キャッシュ | JRA+NAR | 1 | `app.py` | `arvexq/components/item_086/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 147 | 発走前スナップショット | JRA+NAR | 30 | `arvexq/backtest/freeze_research_candidate.py`, `arvexq/infra/race_stores.py`, `arvexq/prediction/official_course_revision.py` 他7 | `arvexq/components/item_147/prerace_archive.py`, `arvexq/components/item_147/routes.js` | `arvexq/prediction/prerace_archive.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 148 | 保存データバージョン管理 | JRA+NAR | 17 | `scripts/arvexq_fetch_d1_bundle.py`, `scripts/arvexq_freeze_predictions.py`, `scripts/arvexq_migrate_full_snapshots.py` 他3 | `arvexq/components/item_148/full_snapshot_codec.py`, `arvexq/components/item_148/api_forecast_revisions.mjs`, `arvexq/components/item_148/api_snapshot_export.mjs` | `arvexq/ingest/full_snapshot_codec.py`, `workers/api_forecast_revisions.mjs`, `workers/api_snapshot_export.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 149 | キャッシュ期限・破棄 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_149/routes.py`, `arvexq/components/item_142/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 151 | Full Prefetch | JRA+NAR | 11 | `app.py` | `arvexq/components/item_151/race_priority.py`, `arvexq/components/item_151/routes.py` | `arvexq/pipeline/race_priority.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 152 | Realtime Sync | JRA+NAR | 11 | `scripts/arvexq_wait_runtime.py`, `app.py` | `arvexq/components/item_152/runtime_readiness.py`, `arvexq/components/item_152/routes.py` | `arvexq/infra/runtime_readiness.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 153 | Result Repair | JRA+NAR | 8 | `scripts/arvexq_restore_result_day.py`, `app.py` | `arvexq/components/item_153/day_index.py`, `arvexq/components/item_153/routes.py` | `arvexq/results/day_index.py`, `app.py` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 154 | History Repair | JRA+NAR | 14 | `app.py` | `arvexq/components/item_154/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 155 | オッズ自動更新 | JRA+NAR | 4 | `app.py` | `arvexq/components/item_155/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 156 | 馬体重自動更新 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_156/nar_official_card.py` | `arvexq/ingest/nar_official_card.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 157 | 天候・馬場自動更新 | JRA+NAR | 1 | `app.py` | `arvexq/components/item_157/race_clock.py` | `arvexq/pipeline/race_clock.py` | 静的照合pass / Stage4境界pass / 部分保留11 / 全分岐・本番未認定 |
| 159 | レース詳細事前生成 | JRA+NAR | 7 | `app.py` | `arvexq/components/item_159/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 160 | 取得失敗時再試行 | JRA+NAR | 2 | `scripts/arvexq_jra_weather_readback.py`, `scripts/arvexq_nar_weather_readback.py` | `arvexq/components/item_160/d1_day_readback.py` | `arvexq/ingest/d1_day_readback.py` | 静的照合pass / 160・175オフラインpass / 全分岐・本番未認定 |
| 161 | データ鮮度判定 | JRA+NAR | 2 | `app.py` | `arvexq/components/item_149/routes.py`, `arvexq/components/item_142/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 162 | 同期状態・エラー管理 | JRA+NAR | 12 | `app.py` | `arvexq/components/item_162/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 163 | レース一覧API | JRA+NAR | 4 | `app.py` | `arvexq/components/item_163/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 164 | レース詳細API | JRA+NAR | 2 | `app.py` | `arvexq/components/item_164/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 部分保留2 / 全分岐・本番未認定 |
| 165 | 馬別情報API | JRA+NAR | 1 | `app.py` | `arvexq/components/item_165/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 166 | 過去走API | JRA+NAR | 1 | `app.py` | `arvexq/components/item_166/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 167 | オッズ更新API | JRA+NAR | 3 | `app.py`, `workers/web.mjs` | `arvexq/components/item_167/routes.py`, `arvexq/components/item_167/live_odds.mjs` | `app.py`, `workers/live_odds.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 168 | 払戻API | JRA+NAR | 1 | `app.py` | `arvexq/components/item_168/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 169 | 環境情報API | JRA+NAR | 1 | `app.py` | `arvexq/components/item_169/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 170 | 全頭診断API | JRA+NAR | 3 | `app.py` | `arvexq/components/item_170/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 171 | 保存状態API | JRA+NAR | 4 | `app.py`, `workers/api.mjs` | `arvexq/components/item_171/routes.py`, `arvexq/components/item_171/api_storage_audit.mjs` | `app.py`, `workers/api_storage_audit.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 172 | ヘルスチェックAPI | JRA+NAR | 2 | `app.py` | `arvexq/components/item_172/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 173 | Cloudflare Worker | JRA+NAR | 2 | `workers/api.mjs`, `workers/web.mjs` | `arvexq/components/item_173/api_entry.mjs`, `arvexq/components/item_173/web_entry.mjs` | `workers/api.mjs`, `workers/web.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 174 | D1接続 | JRA+NAR | 1 | `workers/api.mjs` | `arvexq/components/item_174/api_full_snapshot.mjs` | `workers/api_full_snapshot.mjs` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 175 | APIエラー処理 | JRA+NAR | 2 | `scripts/arvexq_nar_going_readback.py`, `scripts/arvexq_nar_scratches_readback.py` | `arvexq/components/item_175/d1_day_readback.py` | `arvexq/ingest/d1_day_readback.py` | 静的照合pass / 160・175オフラインpass / 全分岐・本番未認定 |
| 176 | ホーム画面 | JRA+NAR | 8 | `app.py`, `arvexq/ui/static/app.js` | `arvexq/components/item_176/routes.py`, `arvexq/components/item_176/routes.js` | `app.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 177 | 開催場一覧 | JRA+NAR | 1 | `arvexq/ui/static/app.js` | `arvexq/components/item_177/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 178 | 開催場別レース一覧 | JRA+NAR | 2 | `arvexq/ui/static/app.js` | `arvexq/components/item_178/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 179 | レース詳細 | JRA+NAR | 4 | `arvexq/ui/static/app.js` | `arvexq/components/item_179/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 180 | 出馬表 | JRA+NAR | 11 | `arvexq/diagnosis.py`, `arvexq/horse_detail.py`, `arvexq/odds.py` 他3 | `arvexq/components/item_180/race_card.py`, `arvexq/components/item_180/routes.js` | `arvexq/race_card.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 181 | 馬別詳細 | JRA+NAR | 7 | `arvexq/diagnosis.py`, `arvexq/services/race_analysis.py`, `scripts/arvexq_daily_archive_audit.py` 他1 | `arvexq/components/item_181/horse_detail.py`, `arvexq/components/item_181/horse_review_bank.py`, `arvexq/components/item_181/routes.js` | `arvexq/horse_detail.py`, `arvexq/databanks/horse_review_bank.py`, `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 182 | 過去走表示 | JRA+NAR | 4 | `arvexq/career_missing.py`, `arvexq/horse_detail.py`, `scripts/arvexq_sectional_fix_measurement.py` 他1 | `arvexq/components/item_182/history.py`, `arvexq/components/item_182/assets.py` | `arvexq/history.py`, `arvexq/ui/static/history/view.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 183 | 脚質マップ | JRA+NAR | 1 | `arvexq/ui/static/app.js` | `arvexq/components/item_183/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 部分保留1 / 全分岐・本番未認定 |
| 184 | 展開予想表示 | JRA+NAR | 6 | `arvexq/ui/static/app.js` | `arvexq/components/item_184/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 185 | 予想表示枠 | JRA+NAR | 1 | `arvexq/ui/bundle.py` | `arvexq/components/item_185/assets.py` | `arvexq/ui/static/forecast/prediction_frame.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 186 | 印表示枠 | JRA+NAR | 1 | `arvexq/ui/bundle.py` | `arvexq/components/item_186/assets.py` | `arvexq/ui/static/forecast/mark_frame.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 187 | 買い目表示枠 | JRA+NAR | 1 | `arvexq/ui/bundle.py` | `arvexq/components/item_187/assets.py` | `arvexq/ui/static/forecast/ticket_frame.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 188 | 結果・払戻表示 | JRA+NAR | 15 | `arvexq/ui/static/app.js` | `arvexq/components/item_188/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 189 | リアルタイム表示 | JRA+NAR | 6 | `arvexq/ui/static/app.js` | `arvexq/components/item_189/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 190 | お気に入り | JRA+NAR | 5 | `arvexq/ui/static/app.js` | `arvexq/components/item_190/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 191 | 画面遷移・戻る操作 | JRA+NAR | 10 | `arvexq/ui/static/app.js` | `arvexq/components/item_191/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 192 | 手動更新・プル更新 | JRA+NAR | 5 | `arvexq/ui/static/app.js` | `arvexq/components/item_192/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 193 | PWA・ホーム画面起動 | JRA+NAR | 5 | `app.py` | `arvexq/components/item_193/icon_assets.py`, `arvexq/components/item_193/routes.py` | `arvexq/ui/icon_assets.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 194 | オフライン・キャッシュ表示 | JRA+NAR | 10 | `arvexq/ui/static/app.js` | `arvexq/components/item_194/routes.js` | `arvexq/ui/static/app.js` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 195 | CSS・レイアウト管理 | JRA+NAR | 9 | `app.py`, `arvexq/ui/bundle.py` | `arvexq/components/item_195/assets.py`, `arvexq/components/item_195/routes.py` | `arvexq/ui/assets.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 196 | Python・JavaScript自動テスト | JRA+NAR | 1 | `scripts/arvexq_independence_audit.py` | `arvexq/components/item_196/audit_route.py` | `scripts/arvexq_independence_audit.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 197 | JRA・NARデータ検証とバックテスト | JRA+NAR | 2 | `app.py` | `arvexq/components/item_197/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 198 | GitHub Actions CI・PWAビルド | JRA+NAR | 2 | `app.py` | `arvexq/components/item_198/bundle.py`, `arvexq/components/item_198/routes.py` | `arvexq/ui/bundle.py`, `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |
| 200 | ログ・障害監視 | JRA+NAR | 7 | `app.py` | `arvexq/components/item_200/routes.py` | `app.py` | 静的照合pass / Stage4境界pass / 全分岐・本番未認定 |

## 項目125

`scripts/arvexq_verified_holdout.py` は `arvexq.components.item_125.preoff_evidence_store.open_store` を経由し、`arvexq.forecast.verified_holdout.evaluate_verified_circuits` をimportしている。現main/PR HEADに `arvexq/forecast/verified_holdout.py` は存在せず、該当CLIのimport段階で失敗する。箱125の他8接続recordとCLI全体の正常動作は別。ロジックの新規作成・既存研究の復活が必要なので、125の未解決CLIだけ保留。元の予想方式・保存原本に変更なし。

## ステージ6 CI（`d5b5e426ca79218e65e1ef6a384fd6f7563de566`）

- Python 全pytest 1609 pass / 0 fail / 3 skip、37 subtest pass。stage4 shared45件、stage5 tests3件、stage6 offline integration9件、178項目source契約178件を含む。
- `ARVEXQ Independent Components` pass、既存D1/環境モジュール等pass。
- `ARVEXQ Validation` はpytest後に `scripts/arvexq_race_source_integrity_smoke.js` の旧 `openRace` 本文抽出アサーションでfail。実装 `app.js` は既存箱転送＋private元関数で保持。テストファイルはPR #368/#112競合対象のため変更しない。
- `ARVEXQ History Result Verification` は過去帯広レース `nar-2026-03-20-帯広ば-05` の本番APIが404でfail。既存取得経路/サーバー側を無断変更しない。
- `ARVEXQ Recovery Regression` はブラウザースモーク `revisionTest is not defined`（既存ブラウザー検査）と、本番WebKitのAPI CORS/アクセス失敗の疑いでfail。接続変更由来と断定せず、UI・本番を変更しない。
- `scripts/arvexq_design_freeze_smoke.cjs` と `scripts/arvexq_saved_ticket_smoke.js` は箱転送後も保持されている元実装を対象にテストを修正し、該当手順が成功した（前段続行のコミット `4ba9a461`）。Python/GitHubの変更はPRブランチのみ。

## main入出力比較と未実施

Stage4の176項目について過去にmainとのPython 32実データ系ケース、HTTP5、OpenAPI122パス、UI19、Worker9の等価検査を保存。Stage6で同じ全経路比較を再実行したとは主張しない。160・175の箱は元 `read_day` オブジェクトそのものを転送（専用pytest・オフライン統合）。本番D1・実プロバイダー・長時間ループ・全馬の能力/脚質/展開/確率/印/おすすめ買い目の実際の一致は未検証。保留22項目、競合41関数/76ファイル、部分保留15項目は無断変更なし。main統合・デプロイなし。
