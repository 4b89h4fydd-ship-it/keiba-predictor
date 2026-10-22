# 第4段階：176項目のオフライン結合検証

対象：Draft PR #386、接続コード e6f4f2a0e5d64e13c0c0ca7cb32d8db6aa77d6da、最新main 6f21f2e595df17f840c785c31a9f1c5a802bb169、Issue #371。開始時に全36 open PRのheadを照合し、#386以外の35件は第3段階の競合台帳と一致。

## 結果と判定の範囲

- **176/176項目、621接続recordの境界契約を検証**。これは全項目の全分岐・実データ・本番動作成功の認定ではない。項目別は [RESULTS.md](RESULTS.md)、機械可読の対象/保留は [item-results.json](item-results.json)。
- 全pytest **1,375 pass / 0 fail / 0 skip**（別途37 subtest pass）。後から追加した共有alias検査 **45 pass**。同じ再実行コマンドで全件走らせる場合は1,420件になる。
- Pythonの291 aliasは元object/moduleとの同一性、208公開転送は実公開入口→箱→spyの引数/返値/例外/signature/asyncと単一実行、asset9件は元文字列、audit転送1件を確認。関数内import/削除済installer名のimport文単独実行は、その関数/CLI全体の実行成功と区別。
- Node：102 UI転送契約、8 ESM同一性、2 Worker転送契約。mainとの実処理比較はPython32ケース、HTTP5経路、OpenAPI122パス全定義、UI19ケース、Worker9ケースで一致。入力変更後の構造も比較。圧縮保存原本の復元、失敗応答、静的asset、JRA/NAR既存IDを維持する比較でDB呼び出し列も一致。
- 静的PWAはmain/候補ともビルド成功。配布ファイルは7件のみ差分：2 JSの第3段階転送と5 HTMLの既存cache hash。HTML構造/CSS/画像/保存archiveは一致。本番公開していない。
- 一時DBを使用し、外部socketを遮断。ループ起動フラグを無効化。localhostだけ既存readinessテスト用に許可。本番API/D1/取得先への通信・書込みなし。Actions手動起動なし。

## 修正

本番処理コードの不具合は検査範囲で再現せず、**runtimeコード修正0件**。予想方式・取得先・データ構造を変更していない。

競合対象外の既存テスト13ファイルだけを接続構造に追従させた。Pythonの本文/AST抽出11ファイルは、公開転送と保持された元実装を区別するhelper経由にし、元の業務assertionを維持（サイズ制約は転送を除く実装サイズに適用）。Node2ファイルは公開関数・保持元本文・対応箱helperを一緒にロード。loading smokeの古い期待文言はmainにも既にある表示文言へ更新し、UIを変更していない。新しい境界テストは実公開wrapperを直接実行し、本文抽出テストだけで接続成功とはしていない。

## 未解決・保留

- 部分保留15件（020,021,022,040,057,110,113,127,153,154,157,162,164,179,183）：接続recordの範囲は境界検証済み。各deferred関数/asset/workflowは未検証・未変更。詳細は項目別JSON/Markdown。
- 125：open_storeのaliasとUI転送は確認。既存研究CLI scripts/arvexq_verified_holdout.py はmain/候補両方に存在しない arvexq.forecast.verified_holdout をimportしておりCLI全体を検証できない。既存予想系統の復活・新モジュール作成で補完しない。
- 未接続24件は変更0（番号はsummary.json）。競合対象41関数・76ファイル変更0。保護対象のsha256はpreservation.json。新しい競合の上書きなし。
- 実取得先の全HTML変種、全履歴、長時間バックグラウンド、実ブラウザー操作、本番動作は未検証。すべての業務分岐の網羅は認定しない。オフラインケースで未再現のエラー/二重実行/欠損が不存在とは断言しない。
- 既存独立化監査CLIはexit 0、errors=[]、complete=3/200、remaining=197、判定「未完了」。これは既存requirementsの別基準。原本manifestを編集して数字を176へ変えていない。

## 再実行

依存：requirements.txt、pytest、httpx、Node 24。baselineは上記main SHAをcheckoutした別worktreeを用意。

```bash
python scripts/arvexq_stage4_offline_tests.py --baseline /path/to/main-worktree --output /new/local/evidence-directory
```

スクリプトは既存pytest、Node契約/既存smoke、元監査CLI、mainとのruntime比較を実行し、外部socketを遮断する。元データ/本番環境を使用しない。PWAビルドの比較は別途両worktreeで python build_static.py を実行した記録。

証拠：summary.json、pytest.log、pytest.xml.gz、shared.log、node-contracts.log、runtime-fixtures.json.gz、build-comparison.json、preservation.json。fixture JSONはmainと候補で同一のため1コピーとSHA256を保存。対象runtime sourceはe6f4f2a0から無変更。変更ファイルのhashはfile-manifest.json。

**第4段階の検証・テスト修正・記録で停止。第5段階、main統合、本番デプロイ、200項目の完了認定は行わない。**
