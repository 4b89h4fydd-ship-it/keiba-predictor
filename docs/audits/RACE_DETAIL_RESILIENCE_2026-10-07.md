# ARVEXQ レース詳細取得の復旧

## 調査結果

2026-10-07 大井11Rの一覧ID・詳細要求IDは `nar-2026-10-07-大井-11` で一致。確認時の詳細APIはHTTP 200、16頭・16件のオッズ、距離2000m、発走20:05。応答は約3MB。障害発生時点のサーバーログは取得できないため、その時のHTTP原因は断定しない。

一覧APIには `fieldSize` がなく、旧画面が未取得の `horses=[]` を頭数0としていた。旧 `openRace` / `reloadCurrent` は出走表がないと一覧情報を破棄して全画面の同期待ち表示へ移行。当日キャッシュは2分を超えると読み込まなかった。旧 `/api/race` は履歴・診断・結果・オッズをまとめて返し、基本的な出走表もその大きな応答の成功に依存していた。

NARの公式取得設定は大井 `k_babaCode=20`、日付 `2026/10/07`、レース番号は整数 `11`。netkeibaの大井コード44とは別。IDのレース番号は2桁、APIのパスは `encodeURIComponent(id)`、WorkerでdecodeしてD1のrace_idと照合する。今回はID・公式取得仕様を変更していない。

## 変更

- 一覧の基本情報を即描画。頭数不明は「頭数取得中」、明示的な0頭だけempty。
- `GET /api/racecard/<race_id>` を追加。D1のJSONから基本情報・出走馬だけを投影する読取専用経路。schema/migration/保存処理は変更しない。
- `GET /api/race/<race_id>?view=display` を追加。未使用の学習用 `massFeatureSnapshot` だけをD1読込時に除き、約3MBを約560KBへ縮小。従来API・保存snapshotは維持。表示向け応答でもオッズ問い合わせ失敗を隔離。
- 出走表、既存 `GET /api/odds/<race_id>`、従来の詳細・履歴・診断の取得を独立させた。出走表だけのデータから診断を捏造せず、詳細の取得を待つ。
- 出走表を先に描画してから既存予想を計算。診断・装飾の例外はその項目だけに隔離。
- 対象レースのstale cacheを表示し、裏で更新。全キャッシュ削除なし。
- 自動詳細取得は最大3回、1秒/2秒のバックオフ。手動再試行は新しいfetchで、他レースの失敗状態やキャッシュには触れない。
- race_id不一致・HTTP失敗・項目の例外は限定件数の診断トレースへ記録。
- 馬詳細ダイアログの既存描画呼び出しを復旧。固定ヘッダーより手前に配置し、取得済み近走5走の表示と閉じる操作を検証。
- 均等幅タブを維持。レース名はカード内で横幅を確保し最大2行にし、発走時刻と重ねない。
- 旧JS/CSSを再利用しないよう、asset URLの修正識別子を更新。

## 検証

- 障害テスト7ケース：503→基本情報維持→新規retry復旧、詳細503中の独立出走表/オッズ、stale cache、オッズ/履歴不足+診断例外、オッズ形式不正+診断表示例外、確認済み0頭、別race_idの拒否。
- 大井11Rの実データで同じ障害テストを実行。
- 大井11Rの予想オブジェクト全体の修正前後SHA256は一致：`6ba7ef0f8b4d1b00b96e6f3bec07e5bc6cb60a9c4e9b886e3f80b30bc63eb0f0`。
- 320/375/390/430/768pxで2種類の選択状態を検証。幅・高さ一致、色・フォント・padding・影維持、下段タブの寸法維持。
- 新APIはread-only SQLで16頭のID/名前/基本情報が一致し、応答約5KB。Worker単体テストで通常/empty/404/503とSafari CORSを検証。
- 調査時の履歴は16頭中14頭に実走あり、2頭は未取得。5走がない馬を架空の履歴で補わない。

## 変更ファイル

main: `arvexq/ui/static/app.js`, `styles.css`, `index.html`, `scripts/arvexq_detail_resilience_smoke.js`, `.github/workflows/arvexq-webapp-race-smoke.yml`, 本報告。
cloudflare: `racecard.js`, `worker-entry.js`, `tests/racecard.test.js`, `package.json`, `.github/workflows/arvexq-cloudflare-validation.yml`, `.github/workflows/arvexq-api-deploy.yml`。

APIの公開は成功し、新しい出走表APIはHTTP 200・16頭・4960bytesを確認。既存Cloudflare Validationの全日詳細（details=1）GETによるCORS検証は再実行しても失敗。OPTIONS、構文、Worker単体テスト、dry runは成功し、全日一括の重いGETは今回変更していない。
