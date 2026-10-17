# 2026-10-17 実行結果（全面完成ではない）

## 実際の実装とローカル検証

- `e4c99c6` から再開。最新main `3d76a28` を開発ブランチへ取り込み、Recovery workflowと本番smokeの競合を解消。mainのDOM契約検証と開発側の意図的API停止時の限定エラー検証を両方維持した。これはmainへの新方式統合ではない。
- NAR公式CSVの生年月日・調教師・血統・公式時計を全履歴providerに渡す。着差秒は同じ公式レースの勝馬時計と対象馬時計が双方確認できる場合だけ算出し、証拠を保持。テキストの着差を秒と仮定しない。
- 複数ZIPで同一レース・馬番に矛盾する馬名／生年月日があれば拒否する。履歴照合の同名馬判定にも対象日以降の行を使わない。
- 候補モデルv2に全体・近走・同距離・同競馬場・同回り・同条件・直近同条件の勝率／連対率／3着内率とWilson 95%信頼区間を追加。近走・回り・同条件・直近同条件の率、標本不確実性、観測できた厩舎継続・転入を学習特徴へ追加。固定能力加重点は追加していない。
- 各展開の同一着順分布から1着・2着内・3着内確率を集計し、構造化データにはパーセント範囲も出力。平地・障害・ばんえいの履歴を混在させない。位置取りが不足して単一展開しか作れない場合は、文章でも複数展開を比較済みと説明しない。
- 削除済み45/35/20モデルに依存していた古い検証を修正。観測フィールド保存テストを維持し、廃止モデルを復活させない。退役モデルを必要とする2本の古い比較CLIは明示的に退役エラーを返し、公式結果パース／集計の再利用関数は保持。
- Python全体: unittest 442件成功（3件skip）、pytest 451件成功・39 subtests成功。既存Validationの実行コマンド24ステップをローカル実行し全成功。ブラウザーバイナリのローカル取得は壊れたZIP応答で失敗し、Playwrightブラウザー実行はローカル未完了。
- CIに全pytestを追加。開発ブランチのpushでもRecoveryを実行するよう変更。新コミットのGitHub側CI結果はIssue #217の追記で確定する。

## 新規取得した実公式データ

NAR公式日次ZIPと2026年1～10月月次ZIPをHTTP 200で新規取得。SHA-256・取得完了時刻は `20261017-execution/official-source-manifest.json`。月次ZIPには未発走の日付も含まれるが、モデル用履歴は対象日より前に限定する。

- 2026-10-17: **34レース、公式頭数341、取得341（100%）**。馬番の重複排除後、全レースで公式頭数と取得頭数が一致。
- 当日の生年月日・騎手・厩舎・斤量の空欄: **0頭**。
- 正規providerと同じ馬名／生年月日照合で、対象日前の有効着順を持つ履歴あり **329/341頭（96.48%）**、履歴なし **12頭**、5走未満 **43頭**。無効着順を除外し、対象日以降の同名馬情報も照合に使わない最終コードで再測定。
- 11本の実ZIPを既存 `NarSync.import_zip_bytes` でSQLiteへ取込: **12,292レース、125,907出走行**。閉じて再度開いて125,907行を確認、`PRAGMA integrity_check=ok`。
- 上記は取得アーカイブ内の確認可能な範囲。JRA在籍期間や2025年以前を含む生涯履歴の完全取得は証明していない。12頭が全て未出走馬であるとも断定しない。
- JRAホームはHTTP 200で取得できたが、公式出馬表・番組ページはAkamaiのHTTP 403、既存POST経路はタイムアウト。公式の全頭新規取得は0レースで、分母が確定しないため取得率を捏造しない。本番APIの日別一覧HTTP 200は確認したが、公式からの新規取得成功の代替には数えない。

## 精度の実測と採用判定

v2を既存の2026-10-12学習・10-16評価データで再診断。既に使用した日付であり、発走前取得時刻の完全な証拠もないため、未使用データの受入検証ではない。

| 地方の既存データ診断 | 結果 |
|---|---:|
| 対象 | 36レース |
| ◎採点可能 | 25レース |
| 全頭履歴不足 | 11レース |
| ◎1着 | 10/25（40%） |
| ◎3着内 | 17/25（68%） |
| 推奨／見送り | 0／36 |
| 推奨買い目的中率・回収率・平均点数 | 算出不能（購入0件・0円） |

中央の当該評価日は0レース。80%達成は未確認。v1の12/25・18/25よりこの診断では低下した。結果を見て同じ評価データに係数を合わせることはしていない。新候補は未校正であり、本番へ採用しない。

## 未完了と阻害要因

6工程はいずれも全受入完了ではない。①NAR当日出走表の頭数検証は成功したが、JRAの取得拒否、NAR12頭の履歴不足、生涯網羅未確認が残る。②新候補の校正、展開発生頻度・異クラス換算等は未実装。③全券種候補比較はあるが、実測済みおすすめ選択は未完成。④中央地方各30以上の未使用日・発走前証拠限定の評価は未達。⑤Web/API/D1への新候補の接続は未実施。⑥CI確定、mainへの新方式統合、本番反映と新方式の実動作検証は未完了。

Cloudflare API token／account認証・SYNC_TOKENはローカル環境にない。リポジトリに既存デプロイと保護バックアップworkflowは存在するが、この実行でD1完全バックアップ／復元を検証した証拠はない。受入未達の候補をmainに統合・本番反映したり、発走前原本に事後分析を書き戻す操作は行っていない。既存本番データ／履歴には書き込んでいない。


## 継続検証

ローカルからJRAが拒否されたため、既存の公式取得関数とNarSyncをGitHub Actionsの隔離したデータ領域で実行する入力受入workflowを追加。中央地方それぞれ30レース以上・公式頭数と取得馬番の一致を検査し、失敗時も実応答と集計をartifactへ残す。この入力受渡し検査が成功しても、生涯履歴完全性や精度受入の合格とは扱わない。

pushとPR synchronizeの重複で同一headの本番巡回が並走することを実際に確認したため、Validation／Recoveryのconcurrencyキーを開発ブランチ名で統一。同じコードに対する不要な同時本番アクセスを抑止し、429を成功扱いする変更は行っていない。


## JRA取得阻害の解消と印の根本修正

GitHub Actions run 38989790024では既存公式取得経路が成功し、JRA **36レース・471頭・確認過去走1,625件**を新規取得した。履歴あり405頭・なし66頭。生涯完全取得ではなく、初回取得は表示用4～5走が中心である。初回のJRA fieldSizeは同一パーサーの取得頭数に由来するため、それだけで独立した全頭取得率100%を証明したとは扱わない。続けて公式HTMLの馬ID数との独立照合、既存の公式プロフィールadapterの500走要求、表示5走と全確認履歴の分離を同workflowに追加して実行する。

本番Recoveryの歴史ページで「◎複数」を検出。調査により独立軸の固定加重点と、コア印が空欄でも軸ラベルから◎を増設する表示処理が残っていた。新しい現在予想では独立軸の計算・昇格を削除し、勝ち切りと軸の馬番を同一化。画面説明も一頭の本命に統一する。保存済みの旧原本は保持し、旧役割は「保存印」と区別する。ブラウザーのpolicy識別子を追加し、新policyでは◎一頭を強制する。未配備の旧本番の互換性検査を新policy実動作成功と取り違えない。

## Saved forecast replacement follow-up (verified, not an accuracy acceptance)

- Published `9fa5ea207e7067bef03a6a3e3d6dc369667fe9ea` and Cloudflare preflight `baa30f8b0bc71a3dfd17627db4201469b7968aeb`.
- Official input run 38991646038 passed: JRA 36 races, 471 numbered runners plus one explicitly unnumbered withdrawal, 472/472 registered entries; 4,507 observed prior runs, 405 runners with history and 66 without. Trainer, jockey, weight and name missing counts zero. Lifetime completeness remains unproved.
- NAR same run: 34 races, 341/341 entries, birth date/jockey/trainer/weight missing zero. Four-month runner archive provides earlier valid history for 316/341. Separate ten-month local audit improves this to 329/341; neither proves lifetime completeness.
- CI 38991720254 Validation passed. CI 38991720251 browser and production-baseline recovery passed. Exact new saved-revision mobile rendering and outage tests passed in its browser job. Production-baseline passes are not evidence the new code was deployed.
- Local full suite after additive backup changes: 457 tests and 39 subtests passed; 24 validation workflow steps passed before those small follow-up changes.
- Complete D1 backup run 38990502928 passed, restored SQLite verified: 2,969 original race details, 2,969 summaries, 6,191 current odds, zero odds history, 74 metadata rows. Original SQL writes zero.
- Cloudflare preflight run 38991717045 passed; existing API source SHA256 `d84dde33b51db45517a64caa5f2be290f73e74fe79652b1fd284bbcd2d2f3df5` was preserved and D1 binding verified. API source guard updated to this actual verified hash.
- New saved forecasts use additive D1 tables and latest-display pointers. Pre-off originals remain byte-for-byte in the original tables. Past-date revisions are labelled retrospective and excluded from original forecast hit testing. All eight ticket kinds remain compared, with a ten-point bound.
- Bulk recalculation is running against the verified backup. Completion counts and production replacement remain pending. New model remains uncalibrated; all-skip betting output is NOT accepted as a successful betting model. Untouched evaluation, calibration, 80% recommended hit rate, live new-race model authority and removal of remaining fallback authority remain open.
