# ARVEXQ 全入口・全経路照合 / 2026-10-20

## 判定

**全入口の列挙・ソース上の照合を実施した。全経路の本番実動作成功は未確認であり、完了扱いにしない。**

前回の1,403ファイルの検索だけを全経路確認として扱わない。今回は実際にimportしたASGI登録、200責務箱、全workflow、Pythonの直接呼出し、Worker相対import、画面通信、保存処理の文字列SOURCEも対象にした。`http-routes.csv`は全127登録を省略せず記録し、動的解決が残る呼出しも件数を明示する。

対象は最新main `9096e47b7c5ddcc6fe9310149ac2df1132078cf9` と、PR #375 `8b72d7b94f3380022d098ef0d8b1966f480182ab` の同一treeからの追加修正。mainは別の隔離worktreeで確認。全34 open PRのhead/baseを再取得した。#374は`e3485d7d`のまま、#367/#368/#369/#370などの担当ブランチを上書きしていない。

## 全対象と証拠

| 対象 | 確認内容 | 結果・限界 |
| --- | --- | --- |
| main | 657ソース、2,247関数、127 HTTP登録、58 workflow | 現在配備されている可能性のあるコードを隔離して比較。本番配備そのものを証明しない |
| 修正候補 | 1,643ソース、2,884関数、127 HTTP登録、200責務箱、58 workflow | 直接呼出し先・保存/通信・importを台帳化。動的呼出しを自動で解決済みとしない |
| 中央取得 | JRA公式、公式過去結果、既存netkeiba補完、既存環境設定feed | 既存取得元登録と実装を追跡。JRA公式の既存transportは実接続成功（91,836文字、JRADBリンクあり） |
| 地方取得 | NAR日次/月次ZIP、ローカルCSV、出馬表/結果/オッズ公式、既存netkeiba補完 | 全取得元の登録・実装・補完を照合。公式の別HTML形式を勝手に新規取得元と判定しない |
| 保存 | NarStore/CentralStore/RaceDB/PreparedStore、圧縮・同期保護・原票 | 文字列SOURCE内のclass/methodも展開して台帳化。既存SQLite/D1保全テストを実行。本番D1書込なし |
| HTTP | FastAPI 123アプリ登録＋4標準docs登録 | 123件は実ルーターで全件dispatch成功。ただしhandlerをstubにした振り分け検査であり、取得/保存処理の成功件数ではない |
| 画面/配信 | 静的GET、全asset alias、Worker、JS相対import・通信箇所 | 88 GETは本物のhandlerで200。47本の既存Validation Node検証が合格。ブラウザ描画は未検証 |
| ジョブ | 全58有効workflow | shell/埋込Pythonの構文319検査すべて成功。削除済Pythonエントリを実行する呼出しは修正後0 |
| 既存研究 | 過去研究、stage63/stage64、既存の未接続研究ソース | 原本保持。稼働workflowから外れた旧研究に9件の欠落import参照が残る。現行モデルを復活させて埋めない |

## 追加で発見して修正した実行経路

1. `.github/workflows/arvexq-prefetch.yml` は、#366で削除した `arvexq_capture_batch_research.py` を呼んでいた。候補生成の実行stepを削除。
2. 同workflowは `arvexq_apply_learned_overlay.py` を呼び、その出力で正規の`prefetch-payload.json`を置き換えていた。削除済別予想による置換stepを削除し、既存事実データの準備→保護→同期→出馬表読戻しを維持。撤去対象モデルだけの読戻し検査も除去したが、`D1_MISSING_CARDS`等の正常データ検査は維持。
3. JRA Margin Source Probeは削除済`arvexq_jra_mineta_observed_comparison.py`を実行していた。古い比較呼出しと生成されないartifact指定だけを除去し、既存公式入力・修復・margin監査は維持。
4. Foundation/Dedup監査workflowは削除済`factor_model`と`today_old_new_compare`に依存していた。別モデルの復活や代替計算をせず、runner YAMLを`docs/research/retired-workflows/`へ**同一bytesのまま保全**し、実行対象から外した。研究スクリプト・過去データは削除しない。

前回のUI別API除去、別予想Worker削除、発走前履歴補完の正規登録への復旧も維持する。新しい取得URL・API・予想ロジックは追加しない。

## 実行した検証

- 全Python: **1,352 passed、45 subtests passed**（既存警告12）。実行行coverageは56.54%。これは分岐網羅でも本番確認でもない。動的compileされたSOURCEは行帰属にも限界がある。
- 追加修正後の対象検証: workflow/取得/回復19件成功、workflow/200箱/結合25件成功（一部重複あり、合算しない）。
- 既存Validationの実行用Nodeコマンド全47本: **47成功、0失敗**。Worker、完全圧縮原票、中央/地方capture、オッズ、出馬表、印/買い目、朝の固定など。ブラウザを必要とする別workflowの成功を代用しない。
- HTTP: **123/123 dispatch成功**、静的画面・asset・health・docsの実handler **88/88成功**。
- YAML全件、shell/埋込Python: **319/319構文検査成功**。構文成功は実APIアクセスや公開成功を意味しない。
- Worker相対importの欠落0、稼働workflowの削除済Python実行先0。

## 実動作が止まった境界

| 境界 | 実際に試した結果 | 現時点の判断 |
| --- | --- | --- |
| 本番API `/api/health`、`/api/day?...&details=0` | この実行環境からHTTP 403。別の読み取りツールでもアクセス不可 | 本番D1→API→UIは未確認。サービス自体の障害や認証原因とは断定しない |
| 盛岡1R/2R 2026-10-20 | 既存`_nar_official_result_fast`が各2種類の既存公式ページを読み、両方`result_marker_missing` | 結果取得は未回復。HTML公開内容/応答/解析の失敗段階を切り分ける必要あり |
| Chromium | 導入済Playwrightと同じCLIで導入を試したがZIPが空/不完全で展開失敗 | 実ブラウザ・iPhone描画検証は未実施 |
| SQLite同時書込み、本番欠損履歴 | 本番修復処理は実行していない | 回復成功とは報告しない |

**main統合・本番デプロイ・本番D1書換えは実施していない。全本番経路の完了認定はできない。**

## 再確認用ファイル

- `evidence.json.gz`: main/修正候補の全ソースhash、全HTTP登録・直接呼出しgraph・未解決呼出し、全200箱、全workflow/step、Worker・JS境界、旧SOURCE内定義、テスト結果、実接続試行。
- `http-routes.csv`: 全127 HTTP登録と検証区分。
- `summary.json`: 件数と圧縮証拠SHA-256。
- 再生成: `ARVEXQ_DATA_CORE=0 ARVEXQ_BOOTSTRAP_WARM=0 RACEDB_AUTO_UPDATE=0 python scripts/arvexq_all_route_audit.py --out /tmp/routes.json`。`ARVEXQ_AUDIT_ROOT`で隔離した既存checkoutを指定できる。ASGI lifespanは起動しない。
