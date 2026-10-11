# ARVEXQ 構造改革・第5段階

基準: PR #14 最終HEAD `19b76d3`。専用ブランチ `refactor/arvexq-storage-stage5`。
PRのbaseは `refactor/arvexq-acquisition-stage4`。mainへの統合・本番公開は行わない。

## 調査と移動順序

1. `infra/legacy_stores.py` と `infra/race_stores.py` の文字列内クラスを実体化。
2. NarStoreをスキーマ・CSV契約・取込・履歴・出走表へ分割。NarSyncは独立モジュール。
3. CentralStore、PreparedRaceStore、DayBundleStoreを保存先別に分離。
4. RaceDataBankをスキーマ・出走表/結果スナップショット・全キャリア・オッズ・解析結果に分割。
5. prepared / RaceDB / day bundleの読込、更新、キャッシュ制御を分離。
6. collectorの状態・ロック・起動・周期・失敗処理を機能別に分離。
7. 基準ソースのAST比較、実SQLiteのDDL・保存出力比較、API結合、全回帰、静的ビルド、Actions。

予想・買い目は既存のスナップショット形式で保存する。計算式、選定基準、DBスキーマを変更せず、表示用5走と全キャリアを別のまま保つ。新しいテーブルや新しいデータ移行は導入しない。

## 依存関係

保存モジュールは `app` をimportしない。PreparedRaceStoreとRaceDataBankは、表示圧縮・除外項目処理・発走時計等の明示したポートだけを受け取る。appの互換コンストラクタは既存呼出しを維持し、テスト時の差替えも保持する。

更新coordinatorは関数ごとの明示的なkeyword-only依存を受け取る。collectorの状態は各 `*_state.py` が所有し、別機能のロックを共有しない。起動イベントの順番、環境変数、既存タイムアウト、TTL、リトライ間隔は維持する。importだけでDB作成・ネットワークアクセス・スレッド起動をしない。

## 移動対応表

詳細なメソッド/関数対応・依存ポート・基準ASTハッシュは [stage5-methods.json](stage5-methods.json)、[stage5-functions.json](stage5-functions.json) に収録する。

| 移動前 | 移動後 | 責任 |
|---|---|---|
| app.pyのパス・CSV行契約 | storage/config.py, storage/nar/contracts.py | 互換形式・保存先 |
| infra/legacy_stores.py NarArchiveParser | storage/nar/parser.py | ZIP/CSV解析 |
| infra/legacy_stores.py NarStore | storage/nar/{schema,imports,history,racecards,store}.py | 地方DB |
| infra/legacy_stores.py NarSync | storage/nar/sync.py | 地方同期/キャッシュ |
| infra/legacy_stores.py CentralStore | storage/central/store.py | 中央DB |
| infra/legacy_stores.py PreparedRaceStore | storage/prepared/store.py | 準備済み保存・固定保護 |
| infra/race_stores.py RaceDataBank | storage/racedb/{schema,racecards,career,odds,analysis,store}.py | RaceDB |
| app.py DayBundleStore | storage/bundles/store.py | 日付別保存 |
| app.py DB接続 | storage/sqlite/connection.py | SQLite接続 |
| app.py Data Core状態/更新 | storage/data_core/{health,refresh}.py | フィールド状態と更新記録 |
| app.py prepared読込/更新 | storage/prepared/{cache,refresh}.py | 保存済みデータと更新 |
| app.py 日付bundle | storage/bundles/{local,assembly,cache,live}.py | ローカル読込・構築・更新 |
| app.py オッズ/払戻保存API | storage/market/{odds,payouts}.py | 保存coordinator |
| app.py collector | infra/collectors/{history,live,commercial,environment,data_core,prewarm,fast_card,odds,racedb,bootstrap}.py | 独立起動・周期・失敗処理 |
| app.py collectorの共有変数 | infra/collectors/*_state.py | 機能別ロック・状態・キュー・キャッシュ |

既に適用済みの一度限りの移行スクリプト2本は終了メッセージを返すstubに変更し、削除したSOURCEファイルへの参照とimport時の書換えを止めた。

## 段階検証

クラス分離後、既存403 Pythonテスト・114 subtests成功。coordinator分離後も既存403成功。最終検証・Actionsの結果は後述。

## 完了構成・削減状況

[実ファイル構成一覧](stage5-folders.txt)、[全ファイル移動対応表（CSV）](stage5-files.csv)、[検証記録（JSON）](stage5-validation.json) を参照。`storage/cache_keys.py` は既存ファイルで変更していない。

| 対象 | 基準 | 第5段階 | 削減 |
|---|---:|---:|---:|
| app.py | 4,105行 | 2,872行 | 1,233行（30.0%） |
| infra/legacy_stores.py | 525行 | 削除・実体化 | 525行 |
| infra/race_stores.py | 546行 | 削除・実体化 | 546行 |

43保存メソッドと64更新/collector関数を分離。保存・collector領域の最大ファイルは `storage/market/odds.py` の244行。すべて500行未満。スキーマ、履歴、出走表、オッズ、解析保存は実際のSQL/処理を所有する。パッケージ以外の空フォルダは作成していない。

`storage/ports.py` はRaceDB/Prepared保存の明示的インターフェース。`storage/cache/` は詳細・出走一覧・volatilityのキャッシュ/ロックを所有。`storage/policies/` は欠損保持と固定済み情報の保護。`storage/sqlite/transactions.py` は読込→保持→更新を同じ書込みトランザクション内で行うための境界。

## 基準との差分を調査した保存保護

通常更新について、5種類のストアのDDL、SQLite全保存内容、戻り値、再読込は基準と一致。NarSyncは実ZIP→CSV→SQLiteまで比較し、URL・ヘッダ・45秒タイムアウト・キャッシュヒット・失敗時の保存内容も一致。

基準コードには、部分データの更新で既存の詳細/結果/全キャリアが失われる経路、強制更新で保存済み買い目が上書きされる経路があった。ユーザー指定の保持条件に合わせ、以下の7保存メソッドに限定して意図した保護を追加した。DB形式と予想計算式は変更していない。

| 保存先 | 意図した変更 |
|---|---|
| NarStore.import_rows | 欠損CSVの名前・枠・距離・賞金・着順・時計・コーナー等で既存値を消さない。予定発走時刻は従来どおり保持 |
| CentralStore.upsert | 部分出走表の既存馬情報を保持。全キャリアをunionし、直近5走と混同しない |
| PreparedRaceStore.put | 欠損項目、最初の固定買い目、sealed予想・監査証跡・朝の保存履歴を保持。forceでも買い目を変更しない |
| RaceDataBank.upsert_race | 同上。保持読込と書込みをSQLiteのBEGIN IMMEDIATEで直列化 |
| RaceDataBank.save_odds | 欠損単勝/人気で既存の正常値を消さず、非欠損の更新は反映 |
| RaceDataBank.save_analysis | 部分解析による正常なシナリオ/馬情報の消去を防止 |
| DayBundleStore.put | 取得失敗で件数が減った不完全bundleによる既存保存の置換を防止 |

固定買い目の比較テストでは、旧実装が別の組合せに置換すること、新実装は最初の組合せだけを保持し、それ以外の出力が一致することを明示している。通常更新の不一致は0。上記欠損・固定保護ケースの差分は意図したものとして個別検証した。取消馬を非空の出走表へ再追加せず、馬体重増減0など意味のある0は保持規則の対象外。

## 最終検証

| 検証 | 結果 |
|---|---|
| Python構文・workflow YAML | 成功 |
| Python単体・API/SQLite結合・全回帰 | 549成功、114 subtests成功、失敗0 |
| 第5段階の追加検証 | 146件成功。ソースAST/依存ポート、SQL・出力比較、全キャリア、固定予想/買い目、欠損保持、並行更新/再起動、import副作用、collector独立性を含む |
| 既存JavaScript回帰 | 16本成功。朝の固定、印・買い目、取消、静的fallback等 |
| 予想式/出力比較 | app.pyの予想/学習/監査等13関数AST一致、31式・中央/地方/新馬/障害、成功 |
| 静的ビルド | 成功。基準の214成果物とSHA-256一致、差分0 |
| 保護領域のソース | UI・予想・厳選・買い目・取得・workers等317ファイルがbyte単位で不変 |
| 既存ファイル全体 | 619ファイル不変。既存変更はapp.py、workflow 2本、適用済み移行script 2本のみ。旧SOURCE 2本は削除して実体化 |
| 分離段階GitHub Actions | [Validation成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38115993667)、[Domain Refactor成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38115995317) |
| 保存保護段階GitHub Actions | [Validation成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38116739498)、[Domain Refactor成功](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38116739484)。Chromium/iPhone WebKitも成功 |
| 最終HEAD GitHub Actions | 新Draft PRのChecksと[ブランチ別実行一覧](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions?query=branch%3Arefactor%2Farvexq-storage-stage5)を参照 |

既存のFastAPI startup/Starletteに関するdeprecation警告13件は残る。ローカルsandbox内で子プロセス実行が制限されたJSテストは許可された実行環境で再実行して成功。Chromium/iPhone WebKitの失敗隔離・買い目レイアウトはGitHub Actionsで実行する。

出力比較は固定したZIP/HTTP/SQLite fixtureで実施。本番DBの更新やライブ取得元の実応答比較は行っていない。予想・選考・画面・第4段階の取得モジュールは不変。

## 残存依存・未分離

- app.pyはFastAPIルート・startup登録・明示的な依存注入・互換コンストラクタを保持する。薄い入口への移行は進んだが、全ルートは未分離。
- Prepared/RaceDBは表示圧縮、除外フィールド処理、発走時計、固定監査のポートに依存する。固定基準は今回変更していない。
- collectorは取得、保存、解析更新を個別callbackとして受け取る。全キャリア収集は第4段階の `ingest/history/harvest.py` とRaceDB career保存を利用する。
- `_compact_display_snapshot`、winner learning、予想構築・監査、volatility・モデル監査API等はapp.pyに残る。計算/判定を含むため今回の保存分離と混ぜて変更していない。
- `arvexq/domain/legacy_evaluation.py`（719行）の旧評価installerは残る。保存installerのexecは撤去済み。
- 巨大なUI JS（4,910行）・CSS、workers/api_preserved.mjs、backtest、live_sync/prefetch script等は範囲外で不変。今後はAPIルート/構成root、評価ロジック、UIの順で別段階の分離候補。
- キャッシュのTTL/無効化ルールは各呼出し側に残る部分がある。データとロックの所有者は分離済み。複数プロセスで共有するRedis等の新基盤は導入していない。

mainへの統合・本番公開は行っていない。
