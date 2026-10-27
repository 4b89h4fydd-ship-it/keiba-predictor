# 新方式完成監査（未完了）

2026-10-26 UTC。main統合・本番デプロイ・既存データ削除は未実施。
この記録とPR作成を全工程完了として扱わない。

## 修正
arvexq/forecast/engine.py の blend 呼出しは opinions/calibration/odds のみを消費する。
研究映像行が存在するだけで videoAppliedToFusion=true と「融合特徴量へ反映」を返す誤表示を修正。
検証候補数と適用済み件数を分け、補正は未適用・検証待ちとする。
既存保存原本は変更しない。
tests/test_forecast_video_application_truth.py は合成契約テスト2件であり、実レース成績ではない。

## 既存経路
README: collect -> D1保存 -> 同一事実readback -> analyze -> 保存 -> PWA。
cloudflareブランチは別系統Workerでありmainへ丸ごと統合しない。
現在の publication.public_race は verified unifiedForecast を優先し、
empirical fusionをライブの独立フォールバックとして呼び出さない。
unified_product は researchOnly=true / probabilitiesCalibrated=false。
新方式が校正済み・全工程完成だとは証明できない。
unified_product.paceStages は異なる感度シナリオの最初の着順を4段階に転用しており、
各段階の全馬位置を推定した証拠ではない。段階別実測/予測へ修復が必要。
予想家の公開予想そのものと手法の代理モデルは区別する。

## MotherDuck読取（my_db.arvexq_analytics.race_snapshots）
417件、distinct race_id 417、2026-10-15〜22。
(race_id,sha256)重複0、race_id/sha256/snapshot_jsonのNULL 0。
中央72、地方345。そのうち帯広36は保全し、評価対象から除外する。
表層結果finishersがないのは盛岡2026-10-20の01/02。
これは圧縮原本や公式結果の不存在を証明しない。
全417件にarvexqFullPayloadがあり、bytes/gzipBase64/sha256/versionを持つ。
表層preRacePredictionが0件でも原本を復元する前に保存予想なしと判断しない。
タイトル/馬場文字列で抽出した新馬候補14、障害候補2は公式本人照合前の候補数。

再現SQL:
```sql
SELECT count(*), count(DISTINCT race_id), min(race_date), max(race_date),
 count(*)-count(DISTINCT (race_id,sha256)),
 count(*) FILTER(WHERE race_id IS NULL OR sha256 IS NULL OR snapshot_json IS NULL)
FROM my_db.arvexq_analytics.race_snapshots;
SELECT race_id FROM my_db.arvexq_analytics.race_snapshots
WHERE coalesce(json_array_length(snapshot_json,'$.result.finishers'),0)=0;
```

## 既存PR #499の実行証拠
HEAD 631d39818f5bfc8c92f0d8b021227dbe6b388362。
Validation run 40212214018 とExisting Forecast Revision UI 40212214084はsuccess。
Independent Components 40212214019 とRecovery Regression 40212213990はfailure。
ログで確認:
- D1 /api/day 2026-10-17 は4回試行後HTTP 429。
- CSS固定検査 legacy_v118_v221.css のハッシュ不一致。
- saved_forecast_revision_browser_smoke.js:32 は actual 0 / expected 1。
過去のCI結果は今回の修正HEADの合格証拠ではない。

## 外部依存と未完了
Firecrawl検索はクレジット不足で未実行。設定を変えて再試行しない。
管理実行環境が起動待ちのため、ローカル全コード検索・復元・実データ追加取得・ブラウザ検証は未実施。
GitHub Actionsは別途結果を確認する。
JRA/NAR/新馬/障害の未使用時系列期間評価、確率校正、券種別ROI、翌日全レース表示、
発走前保存と結果照合は未完了。的中率・回収率の新規実測値は報告しない。

## 今回のGitHub Actions実行結果
コードSHA 36c649b13750102574a2e37d96fa26f58c79cf9c:
Validation 40348403403 success。全Python 1140 passed / 3 skipped / 70 subtests passed。
静的PWA build、保存圧縮、pipeline invariantsも同workflowで成功。
Independent Components 40348403725 failure:
- contracts は既存CSSハッシュ固定検査で停止。
- 実D1読取は10/17〜24の8日、425R取得/425詳細/欠損0（帯広48R除外）。
  日別件数58,80,47,48,48,48,36,60。中央108、地方317。
- 中央は確定精算対象106、通常方式で履歴適格104、障害2を通常方式から除外。
  地方は確定精算対象307。中央2/地方10は確定または精算条件不足。
- 学習実行は中央「fewer than 30 eligible blind out-of-time races」でfailure。
  最低標本数を下げて合格扱いしない。
- 地方は学習90・後続検証49・除外1。
以下はその49件における個別代理手法の研究成績であり、
融合後の本番◎成績、実際の公開予想家の成績、将来発走前成績ではない。
校正重み推定に使われる検証成績を、融合後モデルの独立最終テストへ再利用しない。

|手法|1着|3着内|仮想単勝支出|払戻|ROI|
|---|---:|---:|---:|---:|---:|
|ai:bayes|20/49|32/49|4900|4300|87.76%|
|ai:learned|15/49|30/49|4900|2870|58.57%|
|expert:course|9/49|16/49|4900|8310|169.59%|
|expert:form|17/49|27/49|4900|4640|94.69%|
|mineta proxy|8/49|17/49|4900|1910|38.98%|

精度改善の証明ではない。新規公式過去レースの追加取得・新馬/障害の専用検証・全券種評価は未実施。

## 2026-10-27 継続修復
コード abc10d604c0fc54ff4a46c16129f696e260cccd7。
- mineta_public_pace: anyコーナー判定を最初の観測位置へ修正。後半の押し上げを序盤先行と誤認しない。
  最初の観測コーナーはスタート計測ではない。回帰2件を追加。
- forecast/prediction.js: #499を照合。取消・除外・欠場を除いた全馬の本人一致で原票を表示。
  欠落・重複・馬名違い・原票に残った取消馬は拒否。実JS実行テストを追加。
- app.js: 補助描画失敗時に基本出走表へ戻しても検証済みp.rowsを保持。
  出典のない印は既存visible gateで拒否。実復旧関数を例外付きで検証。
- CSS/レイアウト/保存原本は変更せず、main統合・本番デプロイなし。

Validation 40459933147 SUCCESS: 1144 passed / 3 skipped / 70 subtests passed。
PWAビルド・構文・保存圧縮・pipeline invariantsもsuccess。
Existing Forecast Revision UI 40459933224 SUCCESS。
Recovery Regression 40459933239のproductionジョブ122042289636 SUCCESS:
現行本番の出走表・原票・API障害・複数開催場・JRA/NAR過去日・iPhone WebKitの読取検査。
これは修正候補の本番反映や全レース予想完成を意味しない。
同workflow候補browserジョブは記録時点で依存ブラウザのインストール中。

Independent Components 40459933029 FAILURE:
CSS固定検査未解消。実D1は再度425/425詳細・欠損0だが、中央の未使用期間30R不足で停止。
地方は学習90/後続検証49/除外1。同期間の再実行を新規独立検証と扱わない。
精度改善は主張しない。

環境はspec revision 4でpending/offline。ローカル実行・新規公式データ追加取得・
独立検証期間拡大・4段階モデル完成・新馬障害専用受入・全工程完成は未実施。
