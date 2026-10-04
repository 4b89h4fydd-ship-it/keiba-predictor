# ARVEXQ 競馬展開AI（PWA）

iPhone の Safari から使う競馬予想 PWA です。
中央（JRA）・地方（NAR）の出走表、過去走、オッズを集めて、展開予想と AI 評価を表示します。

## できること

- 日付 → 中央 / 地方 → 会場 → 1R〜12R の順に選択
- 馬齢・性別・斤量、騎手・調教師の成績
- 直近レースのタイム・着順・通過順
- 距離・競馬場・馬場・季節・天候
- 先行馬占有率、脚質マップ、5局面の隊列、A/B/C 評価、◎○▲☆△注 の印

## 全体の構成

| 役割 | 場所 | 内容 |
|---|---|---|
| アプリ本体 | `main` ブランチの `app.py` | データ取得、予想エンジン、画面（HTML/JS/CSS）を1ファイルにまとめたもの |
| 画面の配信 | `build_static.py` → `dist/` | `app.py` に埋め込まれた画面を静的ファイルとして書き出す。配信設定は `wrangler.toml`（Cloudflare: `kraizweb1`） |
| データ API | `cloudflare` ブランチの `worker.js` | 画面が読みに行く API（`kraiz-api` Worker / D1） |
| データ更新 | `.github/workflows/` | GitHub Actions が `app.py` を動かしてデータを集め、API（D1）へ送る |

> `cloudflare` ブランチは API Worker の本体です。`main` とは別物なので、マージや削除はしないでください。

## ファイル構成（main）

```
.
├── app.py                  アプリ本体（FastAPI）
├── build_static.py         画面の静的ファイル書き出し（BUILD_VERSION を app.py と合わせる）
├── backtest_v206.py        予想モデルの検証（地方）
├── backtest_v208_jra.py    予想モデルの検証（中央）
├── requirements.txt        Python の依存ライブラリ
├── wrangler.toml           Cloudflare の配信設定
├── docs/audits/            修正時の監査メモ・調査報告
└── .github/workflows/      GitHub Actions（.yml だけを置く）
```

## GitHub Actions

| ファイル | 表示名 | 動くタイミング | 内容 |
|---|---|---|---|
| `arvexq-sync.yml` | ARVEXQ Realtime Sync | 5分ごと（JST 7:00〜23:59）、`app.py` 更新時、手動 | 当日の全レースの出走表・結果・オッズを集めて D1 へ送る。出走表が欠けたレースが残ると失敗扱い |
| `arvexq-history-sync.yml` | ARVEXQ History Repair | 毎時17分、手動 | 過去走データの補修 |
| `arvexq-backtest.yml` | ARVEXQ Backtest v206 | 毎日 JST 23:45、手動 | 地方の予想精度の検証 |
| `arvexq-jra-backtest.yml` | ARVEXQ JRA Backtest v208 | 手動のみ | 中央の予想精度の検証 |

必要なシークレット: `SYNC_TOKEN`（D1 への書き込み用。Sync と History Repair が使用）

## 更新のしかた（iPhone から）

1. GitHub で `app.py` を開き、新しいファイルに置き換えてコミットする
2. `app.py` を更新すると「ARVEXQ Realtime Sync」が自動で動き、データが新しいコードで作り直される
3. 画面のバージョンを上げた場合は、`build_static.py` の `BUILD_VERSION` も同じ値にする（ずれると「ARVEXQを起動中…」のまま止まる）

ファイルは必ず元と同じ場所に置いてください。`.py` や `.txt` を `.github/workflows/` に入れても動きません。

## ローカルで動かす（パソコンがある場合）

```bash
pip install -r requirements.txt
KEIBA_DATA_DIR=./.arvexq-data ARVEXQ_BOOTSTRAP_WARM=0 uvicorn app:app --port 8000
# http://127.0.0.1:8000 を開く

python3 build_static.py   # dist/ に画面を書き出す
```

## データの出どころ

- 中央: netkeiba の出走表・過去走ページ（JRA 公式はフォールバック）
- 地方: NAR 公式・netkeiba

サイトの HTML が変わると取得が壊れることがあります。直近の例は [docs/audits/BUG_REPORT_2026-10-04.md](docs/audits/BUG_REPORT_2026-10-04.md) を見てください。
