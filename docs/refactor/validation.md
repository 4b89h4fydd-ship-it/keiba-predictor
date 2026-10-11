# 検証記録

基準main: `c025fea`。本番の予想・買い目・朝のアーカイブには書き込まない検証。

| 検証 | 結果 | 範囲・補足 |
|---|---|---|
| Python構文 | 成功 | `python -m compileall -q app.py arvexq scripts tests` |
| 全Pythonテスト | 成功 | `pytest tests -q`: **266 passed / 114 subtests passed**。FastAPIの既存on_event非推奨警告12件 |
| Python分離専用テスト | 成功 | 8件。98関数の式・引数、通信・DBなしのimport、全キャリアと5走の区別、固定情報保持、4カテゴリの旧モデル出力 |
| JavaScript分離専用テスト | 成功 | 31関数の原文、中央・地方・新馬・障害の予想行・印・確率・相対評価・展開・順位をmainのfixtureと比較 |
| 配信ソースの一致 | 成功 | Python配信とNode工具の構成表・結合結果をバイト単位で比較 |
| 静的PWAビルド | 成功 | `python build_static.py`、build v329。既存URLと内容ハッシュ更新を維持 |
| Workflow YAML | 成功 | 全workflowをPyYAMLで構文確認 |
| 朝の固定・印固定・公式修正・買い目3系統 | 成功 | morning_picks、mark_lock、frozen_marks、model_mark_revision、three_way_betの各smoke |
| 展開指標・展開遷移・買い目の根拠 | 成功 | six_pace_metrics、pace_transition、pace_evidence_bet_gate、bet_mark_alignmentの各smoke |
| 保存済み券・ID・静的出馬表 | 成功 | saved_ticket、race_identity、static_racecard_openの各smoke |
| 障害時のレース詳細（Chromium） | 成功 | 503×3、カードとオッズの独立回復、staleカード維持、診断例外・展開表示例外の隔離、ID誤結合拒否 |
| モバイル買い目（Chromium） | 成功 | ローカルPlaywrightで実行。WebKitは下記環境制限 |
| morning_picks_runner_smoke | **既存失敗** | `partialDiagnosis.summaries.every(r=>r.morningPickVersion==='v1')`。変更前mainの別worktreeでも同じ失敗を確認 |
| tests/race_loading_smoke.js | **既存失敗** | 古いrendererのHTML文字列の期待。変更前mainの別worktreeでも同じ失敗を確認 |
| ローカルWebKit | 未完了 | ブラウザ本体は導入済み。GTK4等の共有ライブラリが不足、管理者権限なし。GitHub hosted runnerの`--with-deps`による検証対象 |
| GitHub Actions | 実行待ち | PR作成後の結果を追記する |

最初のサンドボックス実行ではasyncio終了処理が停止し、一部テストがtimeoutになった。通常環境で再実行し、全Pythonテストの成功を確認したため、アプリコードの失敗とは分類しない。子プロセスを使うNodeテストもサンドボックスのEPERMを避けて通常環境で実行した。

失敗した古いテストに合わせて朝の選定基準やトップ／読込画面のデザインを変更していない。全体の構造改革は未完了であり、未分離機能・残存依存はREADMEを参照。
