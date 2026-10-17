# ARVEXQ 200項目独立化：実行記録（途中版）

## 完了判定

全200項目完全独立化：**未完了**。本番検証まで全条件が揃った項目は **0/200**。
`requirements.json` に固定ID 1〜200を全件保持する。未解析・未検証を完了に繰り上げない。

## 取得した基準

- main: `a45a84a6f7c737c0169e59163570b68f0e0b4451`
- PR #247: `c81e1fbb4196e9961ba639724a9cde32dc9c2785`
- cloudflare: `e33ebf45d0f988246ed8d1981dcd8055a4557573`
- mainとcloudflareは別worktreeで確認。cloudflareをmainへ丸ごと統合していない。
- 全ワークフロー、Python/JavaScriptソース、Worker、Wrangler設定を取得。

## 実装した変更

- netkeiba出走馬の馬番・枠番・馬名・性別・年齢・斤量・騎手・調教師・馬体重・増減、単勝オッズ・人気をフィールド単位で独立化。
- 旧 `_nk_row_horse` 等の実装をapp.pyから削除し、個別抽出器を合成する新しい呼び出し経路へ接続。フィールド単位の差替えを注入できる。
- 馬体重・斤量・増減の保存前検証を個別責任モジュールへ接続。
- 新モデルを導入せず、production prediction / marks / tickets のインターフェースを別モジュールへ分離。承認済みの方式がないため空を返す。
- API公開時のprojectionを分離。旧予想・印・買い目・保存済み改訂が入れ子の出馬表viewなどから復活する経路を遮断。保存原本と競走事実は変更しない。
- app.pyの旧確率計算 `_build_prerace_prediction` 本体を撤去。
- UIの未使用旧予想・確率・買い目計算52関数を物理削除。一覧は `removed_ui_functions.json`。
- 予想・印・買い目の表示枠と空状態を専用JSへ分離。FastAPIと静的PWAが共通の組立処理を使用する。
- 全頭診断の準備判定を予想エンジンの稼働状態から切り離した。予想廃止によって診断が常に未準備になる問題を修正。
- 旧計算や保存済み候補の表示を期待したテストを新しい廃止仕様に変更。データ、原本の不変性、時系列、取得元、払戻・確定保護テストは保持。
- 200項目の証拠台帳と、未検証の完了計上を拒否する監査スクリプト・専用CIを追加。
- Web本番デプロイ前にPython回帰テストと独立UI契約を実行するゲートを追加。

## Cloudflare変更（別PR #248）

- PR: https://github.com/4b89h4fydd-ship-it/keiba-predictor/pull/248
- head: `96466f4bfa87b50334bf5a463b5f2b13d724f3f5`
- cloudflare統合: `d2868e3ac762cbc1ea2942d36d0e917b8186ffa7`
- PR CI成功: https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39041689758
- 統合後CI成功: https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39041738646
- APIデプロイ成功: https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39041738616
- npm run check: 13テスト成功、スキップなし。
- D1スキーマ変更なし。生の保存原本・管理用監査APIを書き換えない。

## 実測した本番状態

ブラウザで `/api/race/nar-2026-10-07-大井-11?view=display` を確認：

- ok=true、16頭、天候=曇、馬場=良、確定結果、払戻13件。
- predictionStatus=disabled、旧印0、旧予想/買い目/保存改訂の公開なし。
- この対象レースにはrecentRaces/allPastRunsが保存されていなかった。過去走表示の成功証拠には数えない。
- Webホームは起動し日付変更が可能。取得直後は中央・地方0会場の取得待ち表示。全開催・全レースの正常表示証拠には数えない。
- シェルからの本番HTTP取得は環境の403で失敗。ブラウザで上記APIを直接検証した。

## 未完了の範囲

- フィールド分離は主にnetkeiba経路。JRA/NAR公式その他の全経路が項目ごとに独立したとは判定しない。
- B〜Nの全責任・全呼び出し・全入出力・全保存先の個別解析と分離は完了していない。
- app.py、app.js、および既存の動的install/共有globalへの依存が残る。旧方式の全コード撤廃とは報告しない。
- 全200項目の単体/結合/CI/main統合/本番確認は未完了。
- 予想モデル、印の役割、買い目方式は未承認のため、新しい計算を実装していない。
- JRA/NAR全レースの過去走・天候・取消・オッズ・結果・払戻・PWAの実動作確認が必要。

この記録は全工程完了報告ではない。作業内容と本番で観測できた範囲だけを示す。
