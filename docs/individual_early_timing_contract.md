# ARVEXQ 個別テン1F・ゲート反応・初動加速のデータ契約

更新日: 2026-10-08。中央・地方の発走前予想用。数値がない馬へ架空の値を補完しない。

## 計測対象・利用範囲

- **JRA公式レースラップ**: 各200m地点の「先頭馬」を基準とした区間時計。全頭共通のペース文脈に限る。他馬のテン1Fの実測値として代入しない。
- **個別センサー計測**: レースごと・馬ごとに時刻同期した、取得権限のある実測位置・速度ストリームから算出。発走信号と200m到達の時刻差、ゲートが開いた時刻から初回有意な前進検出までの時間、初動速度差から求める加速度をそれぞれ独立に記録する。データ提供者・計測方式・誤差・ライセンスを監査する。
- **映像推定**: 使用許諾のあるレース映像で、ゲート開放・馬の初動・距離基準点をフレーム単位で注釈し、カメラ位置と遠近・フレームレートを較正した場合のみ推定値として保存。距離較正ができない動画でテン1Fの秒数を記録しない。ゲート反応は `(初動フレーム - 開門フレーム)/fps` で表し、フレーム時刻と判定の誤差も持つ。
- **近走初角順位**: 定量化できる個別測定のない馬では脚質・ゲート再現性の**代理指標**として使うが、実測タイムとは呼ばない。

JRA公式の追跡技術はゼッケンのセンサーを利用するが、一般公開されている位置表示と、再解析できる位置ストリームの配布は別問題。一般閲覧画面を無断で抽出しない。JRA公式が2026年6月6日に表示対象を特別・新馬・障害（1競馬場あたり1日最大6競走）へ拡大しても、全レース・全馬の生データ提供を意味しない。

## 過去走へ追加するプロバイダ形式

既存の承認済み HTTPS 馬別履歴プロバイダ（`ARVEXQ_AUTHORIZED_HISTORY_FEEDS_JSON`）へ、**契約上個別計測値の提供権限を確認した場合のみ** `horse_early_timing:true` を指定する。トークンをリポジトリへ書き込まない。

```json
[
  {
    "name": "licensed_individual_timing",
    "circuit": "both",
    "url": "https://authorized-data-provider.example/api/horse-history",
    "token_env": "ARVEXQ_PARTNER_TOKEN",
    "horse_early_timing": true,
    "horse_first3f": false,
    "priority": 25
  }
]
```

以下は**フィールド形式を示す架空のサンプル**であり、実際の馬についての計測結果ではない。

```json
{
  "horseId": "SAMPLE_ID",
  "recentRaces": [
    {
      "date": "2026-09-20",
      "track": "大井",
      "raceNumber": 7,
      "distance": 1400,
      "cornerPositions": [2, 2, 3, 3],
      "earlyTiming": {
        "sourceKind": "individual_sensor",
        "sourceRef": "licensed-provider:measurement-record-id",
        "first200mSeconds": 13.4,
        "gateReactionSeconds": 0.32,
        "acceleration0to100Mps2": 2.8
      }
    }
  ]
}
```

`sourceKind` は `individual_sensor` または `video_estimate` のみ。`sourceRef` は提供元で追跡可能な計測記録ID/映像注釈識別子を必須とする。`official_race_lap`、出所不明、無効な値は個別観測として取り込まず、対象レース当日以降の履歴も遮断する。提供元の宣言のみで数値の真実性を保証するわけではないため、商用導入時は契約・精度・補正方式の検証が必要。

`arvexq/databanks/authorized_feeds.py` が入力検証、`arvexq/ingest/fallback_enrichment.py` が5走への合流・カバレッジ報告、`arvexq/ui/static/app.js` の `horseEarlyTimingProfile` が表示と予想への反映を担当する。予想前のデータだけを対象とする。

## モデル結合と監査

- 個別のテン1Fがあると `ten`、ゲート反応があると `breakRel` を低い重みで補正する。`goProb`、`breakSkill`、`leaderScore`、ハナ候補およびスタート隊列へ既存計算を通じて影響する。
- 個別測定に基づく補正値は確率校正済みの「逃げ成功率」ではない。現在の秒数→点数の正規化は**仮の上限制約付きヒューリスティック**であり、初動・馬場・距離・出遅れの条件別に十分な履歴が蓄積したら校正する。
- 計測値のない馬は初角順位の代理指標を継続し、値を捏造しない。公式レースラップを全馬に複写しない。
- JRA新馬・障害など履歴ゼロの競走を保留にしない。測定値がない旨を表示し、能力・血統など他の根拠から慎重に分析する。
- 実装はデータ入力契約とモデル連動まで。2026-10-08時点で**商用利用可能な個別センサーストリーム契約・本番API認証は未確認**。許諾先の契約がなければ実時計は供給されない。
- 先行時計は取り込んだレース日より未来の出走予想だけに利用。発走後に買い目や発走前の評価を補正し直さない。

## 公式資料・利用許諾

- JRAレース結果の見方: https://www.jra.go.jp/JRADB/mikata/result.html
- JRAトラッキングシステム用語説明: https://www.jra.go.jp/kouza/yougo/to_list.html
- JRA対象レース拡大（2026年6月2日）: https://www.jra.go.jp/news/202606/060201.html
- JRA全周パトロール掲載: https://www.jra.go.jp/faq/pop02/1_7.html
- JRAの映像利用権の取り扱い（2026年4月8日）: https://www.jra.go.jp/news/202604/040801.html
