# 馬プロフィール（血統・馬主・生産者）の収集設計

v348（2026-11-17）で馬詳細パネルに 基本情報（父・母・母父・馬主・生産者）／
血統（3代血統表・兄弟）タブを追加した。本番APIのレース詳細にはこれらの
項目が含まれていないため、表示側は日付別静的JSON
`/horse-profiles/<日付>.json` を受け皿として用意済み
（`arvexq/ui/static/app.js` の `requestHorseProfiles` /
`horseProfileFor`、`build_static.py` のコピーブロック）。
本書は、そのJSONを埋める収集の設計である。**実際のブラウザ収集は
本書の範囲外**（親タスクが既存の材料収集と同じ経路で別途回す）。

## 対象

- その日に出走する全馬（中央・地方、帯広ばんえいは除外）。
- 馬の識別キーはレース詳細の `careerStartEvidence.sourceHorseId`
  （netkeiba の馬ID、例：ポルテボヌール = `2023100948`）。
  取得できない馬は `馬名|生年`（生年 = レース年 − 年齢）をキーにする。

## 対象ページと項目（netkeiba 馬ページ）

馬ページ（馬IDで引ける馬詳細ページ）から、事実データのみを取得する。

| 項目 | JSONキー | 備考 |
|---|---|---|
| 父 | `sire` | |
| 母 | `dam` | |
| 母父 | `damSire` | |
| 馬主 | `owner` | |
| 生産者 | `producer` | |
| 父の父 / 父の母 | `sireSire` / `sireDam` | 血統タブ用 |
| 母の母 | `damDam` | 血統タブ用 |
| 父の父の父 / 父の父の母 | `sireSireSire` / `sireSireDam` | 3代目 |
| 父の母の父 / 父の母の母 | `sireDamSire` / `sireDamDam` | 3代目 |
| 母の父の父 / 母の父の母 | `damSireSire` / `damSireDam` | 3代目 |
| 母の母の父 / 母の母の母 | `damDamSire` / `damDamDam` | 3代目 |
| 兄弟 | `siblings: [{name, wins, note}]` | 取れる範囲で。主な勝ち鞍は note へ |

血統は事実データであり、そのまま格納してよい。netkeiba の文章・
短評・ロゴ等の転記はしない（既存方針どおり）。

## 保存形式・保存先

`arvexq/ui/static/horse-profiles/<YYYY-MM-DD>.json`：

```json
{
  "version": "arvexq-horse-profiles-v1",
  "date": "2026-11-17",
  "horses": {
    "2023100948": {
      "name": "ポルテボヌール",
      "sire": "…", "dam": "…", "damSire": "…",
      "owner": "…", "producer": "…",
      "sireSire": "…", "sireDam": "…", "damDam": "…",
      "sireSireSire": "…", "sireSireDam": "…",
      "sireDamSire": "…", "sireDamDam": "…",
      "damSireSire": "…", "damSireDam": "…",
      "damDamSire": "…", "damDamDam": "…",
      "siblings": [{"name": "…", "wins": 3, "note": "…"}]
    }
  }
}
```

- 血統は馬ごとに不変なので、収集ジョブ側で馬ID単位のキャッシュを持ち、
  未取得の馬だけを新規に取りに行くのが望ましい（日付ファイルは
  その日の出走馬分の和集合として書き出す）。
- 欠けた項目はキーを省略する（クライアントは欠落を「収集中」表示にする。
  推定で埋めない）。

## 収集経路・運用

- 既存の netkeiba 材料収集と同じ経路（ユーザーの iPhone 内ブラウザ、
  `browser=device`）で、前夜・当日朝の収集に相乗りさせる。
- セッションの扱いは既存の厳守事項どおり：ログアウトしない、
  セッションが切れたら再ログインを試みず報告のみ。
- 1日分は出走頭数ベースで最大でも数百頭。馬ページは馬IDで直接引ける
  ため、レースページを経由する必要はない。
