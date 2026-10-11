# 検証記録

基準main: `c025fea`。本番の予想・買い目・朝のアーカイブには書き込まない検証。

| 検証 | 結果 | 範囲・補足 |
|---|---|---|
| Python構文 | 成功 | `python -m compileall -q app.py arvexq scripts tests` |
| 全Pythonテスト | 成功 | `pytest tests -q`: **267 passed / 114 subtests passed**。FastAPI等の非推奨警告13件 |
| Python分離専用テスト | 成功 | 8件。98関数の式・引数、通信・DBなしのimport、全キャリアと5走の区別、固定情報保持、4カテゴリの旧モデル出力 |
| JavaScript分離専用テスト | 成功 | 31関数の原文、中央・地方・新馬・障害の予想行・印・確率・相対評価・展開・順位をmainのfixtureと比較 |
| FastAPI配信の結合テスト | 成功 | 既存のv324互換APIが純粋モジュールを含む同じソースを返し、宣言が利用より先で、予想関数が重複しないことを確認 |
| トップHTML・CSS・固定済みデータ | 成功 | 変更前後の台帳でHTMLと全CSSのハッシュ一致。朝の選定・保存済みスナップショット・静的出馬表146ファイルのハッシュ一致 |
| 配信ソースの一致 | 成功 | Python配信とNode工具の構成表・結合結果をバイト単位で比較 |
| 静的PWAビルド | 成功 | `python build_static.py`、build v329。既存URLと内容ハッシュ更新を維持 |
| Workflow YAML | 成功 | 全workflowをPyYAMLで構文確認 |
| 朝の固定・印固定・公式修正・買い目3系統 | 成功 | morning_picks、mark_lock、frozen_marks、model_mark_revision、three_way_betの各smoke |
| 展開指標・展開遷移・買い目の根拠 | 成功 | six_pace_metrics、pace_transition、pace_evidence_bet_gate、bet_mark_alignmentの各smoke |
| 保存済み券・ID・静的出馬表 | 成功 | saved_ticket、race_identity、static_racecard_openの各smoke |
| 障害時のレース詳細（Chromium） | 成功 | 503×3、カードとオッズの独立回復、staleカード維持、診断例外・展開表示例外の隔離、ID誤結合拒否 |
| モバイル買い目（Chromium） | 成功 | ローカルPlaywrightで実行。WebKitは下記環境制限 |
| morning_picks_runner_smoke | 成功・テスト修正 | mainでも失敗する浅いコピーを修正。1件の未判定カードが他の4件の履歴を消さないfixtureに変更。本番基準は変更しない |
| tests/race_loading_smoke.js | 成功・期待更新 | mainでも失敗する古い文言を現行の読込・情報保持・再取得契約へ更新。画面コード・デザインは変更しない |
| iPhone WebKit | **CI成功** | ローカルはGTK4等不足で実行不可。GitHub hosted runnerの`--with-deps`で320／375／390／430pxのレイアウト・タブ・横はみ出し検証が成功 |
| GitHub Actions：既存Validation | **成功** | [最終コードcd4a890の実行](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38112660380)：構文・ビルド・固定・D1・履歴・補完・運用・結合の全ステップ |
| GitHub Actions：Domain Refactor | **成功** | [最終コードcd4a890の実行](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38112660383)：267 Pythonテスト、ソース一致・式・出力比較、ビルド、固定履歴、Chromium/WebKitの全ステップ |

最初のサンドボックス実行ではasyncio終了処理が停止し、一部テストがtimeoutになった。通常環境で再実行し、全Pythonテストの成功を確認したため、アプリコードの失敗とは分類しない。子プロセスを使うNodeテストもサンドボックスのEPERMを避けて通常環境で実行した。

初回CIで再現した既存テストのfixture共有と古い期待を修正し、朝の選定基準やトップ／読込画面のデザインは変更していない。全体の構造改革は未完了であり、未分離機能・残存依存はREADMEを参照。

初期のAPI配信テストは静的デプロイURLのv329をFastAPIへ要求して404になったため、既存の登録済みv324互換URLを検証するテストへ修正した。FastAPIのルート・予想計算・画面は変更していない。最終コードコミットの検証で残るテスト失敗はない。
