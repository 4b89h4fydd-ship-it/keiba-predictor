# ARVEXQ 構造改革・第4段階

基準は Draft PR #13 の HEAD `95f259597d8663c280b41593bcd3a624630f7f35`。
専用ブランチ `refactor/arvexq-acquisition-stage4`、PR の base は
`refactor/arvexq-domain-separation`。main への統合・本番公開は行わない。

## 調査と作業順

データ管理 → 取得元 → 取得機能を基本とし、JRA は
`arvexq/ingest/central/jra/機能.py` の第4階層まで分離する。

1. 通信・識別子・解析を移す。既存のタイムアウト、エンコーディング、HTTP ヘッダー、キャッシュ規則を維持する。
2. 中央・地方・過去走・出走表・オッズ・結果・補完・環境を移す。ストアや他の取得処理は名前付きの keyword-only port として注入する。
3. ローカル表示と高速取得・全キャリア取得の調整処理を分離し、API と保存まで比較する。
4. 全 Python テスト、静的ビルド、予想・買い目・固定履歴・画面回帰と GitHub Actions を実行する。

## 構造と移動対応

各行の移動元は `app.py`。各モジュールには関数本体があり、逆方向の app import、文字列 exec、名前空間全体の引き渡しは追加しない。
`app.py` の同名関数は互換入口として、元の署名と実行時の差し替えを維持する。
計算・データ形式は変更しない。厳選・特別予想・買い目の計算には触れない。

|移動先（大分類: データ管理 / 中分類: 取得）|小分類・関数|
|---|---|
|`arvexq/ingest/central/feeds.py`|`fetch_central_feed`|
|`arvexq/ingest/central/history.py`|`_central_resolve_race_id`, `_central_recent_from_store`, `_merge_central_recent`, `_central_month_dates`, `_fetch_central_days_parallel`, `_start_central_history_search`|
|`arvexq/ingest/central/jra/calendar.py`|`fetch_jra_official`|
|`arvexq/ingest/central/jra/history.py`|`_jra_parse_past_cell`, `_jra_profile_runs`|
|`arvexq/ingest/central/jra/identifiers.py`|`_jra_norm_cname`, `_jra_attr_cname`, `_jra_program_title`, `_jra_text`, `_jra_iso_date`, `_jra_date_from_cname`, `_jra_race_no_from_cname`, `_jra_track_from_cname`, `_jra_parse_time_seconds`, `_jra_result_cname_from_card`, `_jra_any_track`, `_jra_any_race_no`|
|`arvexq/ingest/central/jra/program.py`|`_jra_program_summaries`, `_jra_program_lookup`, `_jra_find_cname`|
|`arvexq/ingest/central/jra/racecards.py`|`_jra_parse_race`, `_jra_parse_race_summary`|
|`arvexq/ingest/central/jra/results.py`|`_jra_parse_result`|
|`arvexq/ingest/central/jra/transport.py`|`_jra_request`|
|`arvexq/ingest/central/racecards.py`|`central_race_summaries`, `central_race_detail`|
|`arvexq/ingest/environment/parsers.py`|`_env_clean_weather`, `_env_clean_condition`, `_parse_nar_environment_html`, `_parse_jra_environment_html`|
|`arvexq/ingest/environment/providers.py`|`_nar_fetch_environment`, `_jra_fetch_environment`|
|`arvexq/ingest/environment/transport.py`|`_environment_http_get`|
|`arvexq/ingest/history/harvest.py`|`_schedule_full_history_harvest`|
|`arvexq/ingest/local/archive.py`|`sync_recent_history`, `_nar_month_needs_fetch`, `_download_nar_month_only`, `_sync_nar_month_wave`|
|`arvexq/ingest/local/history.py`|`_history_counts`, `_start_race_history_search`, `_race_history_status`, `_nar_attach_recent_batch`|
|`arvexq/ingest/local/odds.py`|`_parse_nar_live_odds_html`, `_nar_live_odds`, `_attach_nar_live_odds`|
|`arvexq/ingest/local/racecards.py`|`nar_race_summaries`, `nar_race_detail`, `_parse_nar_official_card_html`, `_nar_official_card_rows_fast`|
|`arvexq/ingest/local/results.py`|`_fetch_nar_payouts_only`, `_attach_nar_payouts`, `_nar_result_should_be_available`, `_nar_official_result_fast`|
|`arvexq/ingest/merge/current.py`|`_merge_central_odds`, `_merge_result_fields`, `_merge_enrichment`, `_merge_current_card_fields`|
|`arvexq/ingest/netkeiba/history.py`|`_netkeiba_db_horse_history`, `_supplement_sparse_nar_history`, `_netkeiba_past_rows_fast`|
|`arvexq/ingest/netkeiba/odds.py`|`_netkeiba_live_win_odds`|
|`arvexq/ingest/netkeiba/program.py`|`_netkeiba_race_summaries`, `_netkeiba_program_race_id`, `_netkeiba_race_id`, `_nar_netkeiba_race_id`|
|`arvexq/ingest/netkeiba/racecards.py`|`_netkeiba_detail_rows`, `_nar_netkeiba_preview_rows`, `_netkeiba_card_rows_fast`, `_netkeiba_race_meta`|
|`arvexq/ingest/netkeiba/results.py`|`_netkeiba_current_result`|
|`arvexq/ingest/netkeiba/rows.py`|`_nk_row_horse_no`, `_nk_row_frame`, `_nk_row_horse`|
|`arvexq/ingest/netkeiba/transport.py`|`_netkeiba_get`|
|`arvexq/ingest/snapshots/hydration.py`|`_hydrate_fast_card_now`|
|`arvexq/ingest/snapshots/local.py`|`_fast_local_race_detail`|
|`arvexq/ingest/snapshots/results.py`|`_refresh_result_fast`|
|`arvexq/ingest/supplemental/enrichment.py`|`_enrichment_status`, `_start_enrichment`, `_apply_enrichment`|
|`arvexq/ingest/supplemental/feeds.py`|`_format_feed_url`, `_fetch_json_url`, `_extract_smartrc_embedded`, `_fetch_smartrc`, `_fetch_extra_sources`|

関数単位の移動対応・依存は [stage4-functions.json](stage4-functions.json)。
既存関数本体と署名の AST ハッシュを保存し、依存注入以外の変更を検出する。

## 取得元ごとの実行規則

|取得元・機能|タイムアウト / キャッシュ / 失敗・再取得|
|---|---|
|JRA公式通信|`JRA_OFFICIAL_TIMEOUT_SEC` 既定4.5秒。URL+cname キャッシュ。失敗時は例外を返し、失敗を保存しない。自動再試行は追加しない。|
|JRA番組・識別子|番組は当日60秒、過去86400秒。cname検索の現行キャッシュ・liveカード優先を維持。|
|契約中央フィード|`CENTRAL_FEED_TIMEOUT_SEC` 既定12秒。history URL/token → 通常 URL/token。URL未設定の場合だけJRA公式へ。設定済みフィードの失敗を理由に取得優先順位を変更しない。|
|netkeiba通信|呼出機能がtimeout/TTLを指定。URLキャッシュは80件。成功応答のみ保存。履歴、出走表、オッズ、結果ごとの既存値を維持。|
|NAR月次ZIP|既定22秒、ZIP検証、最大6並列取得→同期ロック内で順次DB取り込み。月ごとに取得・保存失敗を捕捉。|
|NAR公式オッズ|既定2.5秒、当日TTL20秒、最大64件。公式→IPAT。forceはキャッシュを回避。既存仕様どおり空結果もキャッシュ。|
|NAR出走表|既定4秒、公式Small→通常→IPAT→SP→sp。全頭が揃うまで不足を補う。|
|NAR結果・払戻|結果既定4秒、払戻既定2秒。各URLの失敗を捕捉して次のURLへ。|
|環境通信|既定2.8秒、呼出元TTL、最大80件。JRA/NARのURLをキーとする現行共通環境キャッシュ。ネットワーク待ち中にキャッシュロックを保持しない。|
|追加フィード|既存URL/token/timeoutと取得元単位の例外捕捉を維持。smartrcは600秒キャッシュ。|

状態を分離したファイルは `central/jra/state.py`、`netkeiba/state.py`、
`local/state.py`、`supplemental/state.py`、`environment/state.py`、`history/jobs.py`
（すべて `arvexq/ingest/` 配下）。8つの追加パッケージディレクトリは
実際の上記機能を持ち、各 `__init__.py` は副作用のないパッケージ説明だけを置く。
状態は JRA、netkeiba、NAR、補完、環境の `state.py` が所有する。
レース単位の履歴進捗は `ingest/history/jobs.py` で共有する。
同一取得元のURLキャッシュ共有と、中央・地方をまとめたレース履歴ステータスは
現行の挙動のため維持し、ロックの粒度や再試行回数を機能追加として変更しない。

## 出力比較と残存依存

基準コミットの取得関数定義だけを圧縮 fixture に保存する。テストで同一の
HTML/JSON/タイムアウトを入力し、戻り値、入力変更、HTTP URL/ヘッダー/POSTデータ、
timeout、キャッシュ内容を比較する。原本 app の起動やネットワークアクセスは再実行しない。
リアルタイムの外部サイトは時刻で内容が変わるため、固定応答によるオフライン比較を用いる。

既存の `NarStore`、`CentralStore`、`NarSync`、`PREPARED_STORE`、`RACEDB` は
まだ旧ストアと保存基盤に依存する。互換入口が必要なportだけを渡す。
バックグラウンド起動、API、予想固定、保存と取得の全体調整は段階的な改善対象として残る。

- `_history_worker` と collector の起動・状態管理は app に残る。
- `_data_core_refresh_race` / `_force_day_live_snapshot` は取得・保存・予想準備を調整する。直接HTTP取得は今回の分離先を呼ぶ。
- 履歴取得は `prediction/career_readiness` と診断用の readiness helper に依存する。これは既存の取得終了判定を保つため。
- `_start_enrichment` / `_schedule_full_history_harvest` は解析と保存の callback に依存する。保存基盤の実体化・トランザクション境界の整理は次の改善対象。
- 既存の `legacy_stores.py`（525行）、`race_stores.py`（546行）、`legacy_evaluation.py`（719行）は変更していない。app 以外のUI・Workers・運用スクリプトの大型ファイルは今回の対象外。

比較中、基準の `_nar_official_result_fast` が結果行の `last3f` を未定義のまま参照する
既存不具合を検出した。移動後も同一の NameError を再現することを検証し、
本PRでは結果計算の修正を混在させない。この直接取得経路の不具合修正は別変更の対象。

## 検証記録

|項目|結果|
|---|---|
|基準 app.py|6,441行|
|分離後 app.py|4,105行（2,336行、36.3%削減）|
|分離関数|90関数、移動元の本体2,843行|
|取得機能モジュール|32ファイル、最大254行。追加したすべてのPythonモジュールは500行未満。|
|app の既存定義|移動対象外の144関数・クラスはAST一致|
|構文検証|`compileall app.py arvexq scripts tests` 成功|
|全Python単体・結合|403成功、失敗0、既存非推奨警告13、114 subtests成功|
|追加検証|90のAST/署名/port検証、31の通信・取得元別ケース、15のSQLite/API/全キャリア/障害分離ケース|
|取得出力比較|固定応答による基準比較の不一致0（既存NAR結果エラーの一致を含む）|
|予想計算・出力|31のJS計算式と中央・地方・新馬・障害の既存 golden 出力が一致|
|静的ビルド|成功。基準と分離後の生成物214ファイルすべてSHA-256一致（ビルドログの70は直下の項目数）。|
|既存ソース・保存履歴|app.pyとCI対象ブランチ設定2ファイルを除く基準の570ファイルがSHA-256一致。UI・発走前・朝の保存データを含む。|
|段階1 GitHub Actions|[Validation成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38114337097) / [Domain Refactor成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38114338580)|

[stage4-validation.json](stage4-validation.json) に行数・各機能モジュールの行数と比較件数を保存する。
第2段階と最終HEADのCI結果はDraft PRのチェックと完了報告に記録する。

GitHub Actionsの変更は、PR baseが`refactor/arvexq-domain-separation`でも
既存の2つの検証workflowが動くようにする対象ブランチの追加だけ。
main push条件と公開用workflowは変更しない。検証は外部サイト・本番キャッシュを使わず、
Python/API、静的ビルド、予想・朝の選定・固定印・保存買い目、Chromium/WebKit画面回帰を実行する。
外部取得元の当日の可用性はこのオフライン構造変更テストの判定対象ではない。
