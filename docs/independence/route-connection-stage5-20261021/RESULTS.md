# 第5段階：未接続24項目の既存経路全件調査と限定接続（2026-10-21 JST）

基点：main `6f21f2e595df17f840c785c31a9f1c5a802bb169` ／ PR #386 `d23cd5e99e27d02baf59cb1f7630dd00273dc615`。Issue #371、既存200項目の allocation.json/connection.json、stage3 STATUS/conflicts/open-prs、進行中PR変更パスを照合した。各行の「元→先」は**既存処理**の経路であり、全実動作・本番検証の認定ではない。

**新規接続2：160、175。残り未接続22。** 176→178項目に接続コードあり。元の621接続recordとは別に、各箱に2件ずつ計4件のcaller import転送を追加。元の`arvexq/ingest/d1_day_readback.py`（PR #369競合）を変更せず、2箱とも同じ`read_day` objectを参照し、取得先・HTTP・戻り値・例外・シグネチャ・中央/地方を変えない。項目125、部分保留15件、予想/UI/データ原本、他PRのコードを変更しない。

|項目|実装・確認ファイルと関数|既存caller → callee|結果／理由|
|---|---|---|---|
|070 着順|app.py `_netkeiba_current_result`, `_jra_parse_result`, `_nar_official_result_fast`|app.pyの結果更新処理（例3267,3219,4922行）→3系統のパーサー→元のfinishers|保留。app.py関数がPR #369/#271と競合。元解析を分割・上書きしない|
|071 着差|app.py 同3関数（JRA/NARの見出し処理含む）|app.pyの更新・結果merge caller→結果パーサー→margin|保留。PR #369/#155/#271と競合|
|072 走破時計|app.py同3関数、arvexq/ingest/jra_time.py `_jra_parse_time_seconds`|app.pyのJRA/NAR結果経路→結果パーサー→時計解析 helper|保留。結果パーサーPR #369/#271と競合。補助jra_timeだけの付替えを時計結果経路完成と誤認しない|
|093 コース適性|arvexq/career_analysis.py `analyze_career`, `_aptitude`|arvexq/career_missing.py→item_057.career_analysis→既存analyze_career→course_type集計|保留。既存callerは全キャリア品質の057役割。予想のコース適性専用consumerを確認できず、057の所有経路を流用しない|
|112 予想ロジック|arvexq/forecast/engine.py `build_prediction`|現行の互換caller→退役済みstub（`None`）|保留。モデル実装は退役済み。新/旧予想モデルを復活しない|
|114 展開シミュレーション|該当稼働実装なし（allocation.json空）|稼働callerなし→稼働calleeなし|保留。研究候補learned_scenarios.pyは稼働元ではない|
|116 印生成|arvexq/forecast/marks.py `generate_marks`、arvexq/prediction/final_marks.py `apply_core_marks`|互換caller→空配列を返す退役stub、別の現行observed_modelへの既存転送|保留。退役stubと現在の印系統を勝手に混ぜない|
|117 ◎【単】|箱allocation.json空|callerなし→calleeなし|保留。既存判断関数未割当|
|118 ◎【軸】|箱allocation.json空|callerなし→calleeなし|保留。既存判断関数未割当|
|119 その他の印|箱allocation.json空|callerなし→calleeなし|保留。既存判断関数未割当|
|120 A・B・C評価|箱allocation.json空|callerなし→calleeなし|保留。既存判断関数未割当|
|122 本線買い目|arvexq/ui/static/morning/ticket_lane_classifier.js `classify`|index.html script読み込み、app.js・scripts/arvexq_morning_picks.jsの既存利用→JS asset|保留。PR #112のasset変更、PR #213のUI build変更と競合。asset順序を変えない|
|123 3連単チャレンジ|arvexq/ui/static/morning/frozen_ticket_evidence.js `capture`, `verify`|index.html script読み込み、app.js・morning_picks.js利用→JS asset|保留。PR #213のビルド/ロードとの調整が必要。保存済み証拠だけを扱う|
|124 買い目点数・配分|同 frozen_ticket_evidence.js 内券種/点数検査|index.html→既存asset→capture/verify|保留。123との共通asset・PR #213のロード順を変更しない|
|134 レース選定結果保存|scripts/arvexq_merge_morning_output.py `merge`/`merge_row`; scripts/arvexq_publish_morning_static.py `morning_manifest`; morning/saved_ticket_receipt.js `recover`|`.github/workflows/arvexq-prefetch.yml`→上記2 CLI→保存済みmanifest；index.html→saved_ticket_receipt.js→既存snapshot|保留。CLIの実行入口は維持。JS assetはPR #213ビルド調整待ち、非package起動CLIへの新規import導入の動作同一性を未確認|
|135 事前/事後区別|arvexq/pipeline/morning_input_policy.js `status`、app.py `_prediction_clock_state`、frozen_ticket_evidence.js|`scripts/arvexq_morning_picks.js`（require）→既存`status`；app.pyの予想時刻caller→`_prediction_clock_state`|保留。app.pyはPR #271、morning_picks.jsはPR #13の変更と競合。別のclock実装を作らない|
|137 前日予想成績|arvexq/ui/static/previous_ai_results.js `load`/集計/DOM描画|独立IIFE asset内→fetchDetail→集計→render；allocation上は別callerなし|保留。稼働読み込みの追加・順序変更はPR #213のビルドとの統合判断が必要|
|143 出馬表キャッシュ|arvexq/storage/cache_keys.py `race_detail_key`|現行稼働caller確認なし→key文字列生成|保留。新キャッシュ経路を作らない|
|144 過去走キャッシュ|同 cache_keys.py `horse_history_key`|現行稼働caller確認なし→key文字列生成|保留。新キャッシュ経路を作らない|
|150 保存失敗時復旧|.github/workflows/arvexq-snapshot-recovery.yml|workflow_dispatch→scripts/arvexq_publish_saved_snapshots.py→build_static.py、保存原本のみgit commit|保留。既存手動workflowはPR #367/#373/#374と構造競合。起動先を変えない|
|158 取消/除外自動更新|arvexq/ingest/official_changes.py `collect_nar_changes`→`fetch_track_changes`→`parse_nar_changes`|scripts/arvexq_live_sync.py:32 import / :533呼出し→既存取得・解析→scratch更新|保留。caller scripts/arvexq_live_sync.pyがPR #369と競合|
|160 取得失敗時再試行|arvexq/ingest/d1_day_readback.py `get_json`、`read_day`|scripts/arvexq_jra_weather_readback.py、scripts/arvexq_nar_weather_readback.py→`item_160.d1_day_readback.read_day`→元`read_day`（default fetch=get_json）→既存HTTP|**2 caller接続**。同一objectのaliasで既存再試行を保持|
|175 APIエラー処理|同 d1_day_readback.py `read_day`、`restore_race_response`|scripts/arvexq_nar_going_readback.py、scripts/arvexq_nar_scratches_readback.py→`item_175.d1_day_readback.read_day`→item_160共有alias→元`read_day`→既存HTTP/例外処理|**2 caller接続**。追加例外処理なし、同じ元関数を共有|
|199 Cloudflareデプロイ/本番確認|.github/workflows/arvexq-api-storage-deploy.yml、arvexq-web-deploy.yml、scripts/arvexq_bound_d1_audit.py `run`|`.github/workflows/arvexq-d1-storage-audit.yml`→`scripts/arvexq_bound_d1_audit.py`、別deploy workflow→build_static/既存smoke|保留。本番権限・workflow経路変更とデプロイは行わない。runは一時Workerを作り削除する既存監査でありデプロイ本体と混同しない|

## 更新ファイル・検証
- 4 caller import行：`scripts/arvexq_jra_weather_readback.py`、`scripts/arvexq_nar_weather_readback.py`、`scripts/arvexq_nar_going_readback.py`、`scripts/arvexq_nar_scratches_readback.py`。
- 追加alias 2：`arvexq/components/item_160/d1_day_readback.py`、`item_175/d1_day_readback.py`。
- 接続記録 2：各itemの`connection.json`（実際に変更した4入口のみ）。
- オフライン回帰テスト 1：`tests/test_stage5_readback_box_aliases.py`。静的importの一致、関数同一性、get_json 503再試行、空日のread_day/error検査。**実行結果が出るまでは合格と宣言しない**。
- スナップショット時点のstage3接続176・621の資料、stage4テスト1,375＋45の結果は**歴史記録として無変更**。全体の接続数は`178/200`、記録付きimport変更箇所は累計625（段階ごとの集計定義に従う場合）。競合41関数・76ファイルは変更対象から除外。
- 実行済みCI・本番/全経路検証はなし。PRの作業ブランチのみ変更、main統合・本番デプロイなし。項目125は無変更。
