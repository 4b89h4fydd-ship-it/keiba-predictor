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

## 検証（作業中）

クラス分離後、既存403 Pythonテスト・114 subtests成功。coordinator分離後も既存403成功。最終検証・Actionsの結果は完了時に追記する。
