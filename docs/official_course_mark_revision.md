# ARVEXQ: 朝の印固定・公式馬場情報に連動した限定修正

## 公表主体の区別

JRA・地方競馬が公表するのは主に馬場状態（良・稍重・重・不良）と、開催場によって含水率・クッション値等の**馬場条件**。内伸び・外有利・前残り・差し有利はARVEXQによる推定であり、公式発表の「トラックバイアス」とは言わない。

JRAによる含水率・クッション値の開催当日の掲載は概ね9時30分頃。朝の初回固定以降に掲載される場合がある。測定時刻と公開時刻を別々に保持する。

- https://www.jra.go.jp/keiba/baba/kaisetsu/
- https://www.jra.go.jp/keiba/baba/
- https://www.jra.go.jp/keiba/baba/index2.html

## 実装済みの安全装置

- 全頭診断が完了し当日の初回レースがまだ発走していない時点に、`scripts/arvexq_morning_picks.js` が同一UI予想エンジンで朝の全頭印を `morningMarkSnapshot` に保存する。取得できない場合は保存未完了とし、過去の予想を捏造しない。
- 通常のオッズ、天候、馬体重、過去レースの結果、AIの再表示では印を変更しない。
- `arvexq/prediction/official_course_revision.py` で、公式ドメイン・対象開催日・開催場・馬場区分・公開時刻・発走前時刻を照合。馬場状態変更、参考基準としてクッション値0.5以上、含水率2ポイント以上の変動でのみ修正を検討する。これはARVEXQの**暫定的な有意差ルール**であり、JRAが保証する有意差ではない。
- `scripts/arvexq_live_sync.py` の開催日5分周期チェックが有効な公式イベントを受けると `scripts/arvexq_capture_course_revised_marks.js` で予想印を再計算し、印に変更がある場合だけ `officialMarkRevisions` へ追記する。修正理由・参照ページ・公式発表時刻・修正時刻・馬番を記録。朝の原本は残す。
- 発走後のイベントは新規反映しない。取消・除外は馬券・馬の有効状態を別処理で表示するが、それだけで正式な「公式馬場変更」扱いにはしない。
- 直前のサーバー封印は朝の原本、または事前に認められた最終修正印を採用。結果照合でも発走前に保存された版のみ扱う。
- `scripts/arvexq_protect_sync.py` はD1への通常同期が原本と既存の有効な修正履歴を消すのを防ぐ。

## 公式情報を自動取得するための接続

GitHub Actions（`arvexq-sync.yml`）では約5分周期で次を参照する。

- Repository variable: `ARVEXQ_OFFICIAL_COURSE_FEED_URL`
- Repository secret: `ARVEXQ_OFFICIAL_COURSE_FEED_TOKEN`

フィードは許可済みのHTTPS APIを想定。返却JSONのトップレベルは `{"events":[...]}`。**以下は形式のサンプルであり実際の測定値ではない。**

```json
{
  "events": [
    {
      "sourceKind": "official_course_condition",
      "sourceUrl": "https://www.jra.go.jp/keiba/baba/",
      "raceDate": "2026-10-10",
      "track": "東京",
      "surface": "芝",
      "publishedAt": "2026-10-10T09:00:00+09:00",
      "going": "稍重",
      "cushionValue": 9.2,
      "moisturePercent": 11.3
    }
  ]
}
```

許可済み配信元が存在しない・認証情報が未登録・公式ページの正規取得が検証されていない場合、**自動収集は稼働しない**。架空の「公式更新」を作らず、朝の印を維持する。原本・修正・結果確定後の不変性はテスト済みの場合と本番動作確認を区別して報告する。

なお、データ提供元から公式ドメインのURLが返ってきても、それだけで真正性が保証されるわけではない。商用提供前に提供者の契約・取得方法・公式根拠の原文・時刻と改ざん対策を監査する。
