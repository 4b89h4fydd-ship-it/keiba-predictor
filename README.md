# ARVEXQ 競馬展開AI（PWA）

iPhone Safariから使う競馬予想PWAです。中央（JRA）・地方（NAR）の出走表、近走、オッズ、馬体重、馬場・天候、結果・払戻を集め、事前計算したAI評価と展開予想をD1経由で表示します。

## 現在の基本構成

| 役割 | 場所 | 内容 |
|---|---|---|
| アプリ本体 | `main/app.py` | データ取得、予想エンジン、FastAPI、画面HTML/JS/CSS |
| PWAビルド | `build_static.py` → `dist/` | `app.py` の画面を静的PWAへ書き出す。build番号は `app.py` から自動取得 |
| 共通処理 | `arvexq/` | fingerprintなど、段階的に `app.py` から分離している共通ロジック |
| 同期処理 | `scripts/` | Prefetch / Live Sync / Result Repair / History Repair / SQLite health |
| データAPI | `cloudflare` ブランチ | `kraiz-api` Worker + D1。`main`とは別系統 |
| 配信 | `wrangler.toml` | Cloudflare Pages/Workers側の静的配信設定 |
| 検証 | `backtest_v206.py`, `backtest_v208_jra.py` | 地方・中央の時系列バックテスト |

> `cloudflare` ブランチはAPI Worker本体です。`main`へ丸ごとマージしたり削除したりしないでください。

## データ更新の考え方

ARVEXQは「画面を開いた時に重い取得・分析をする」構成ではありません。

1. **Full Prefetch** が当日レースの出走表・近走・AI診断を先に作る
2. **Realtime Sync** が5分ごとにオッズ、人気、馬体重、取消、天候・馬場などの変動項目だけ更新する
3. **Result Repair** が発走後の着順・払戻の取りこぼしを補修する
4. **History Repair** が直近7日を巡回して欠損したカード・結果・払戻を補修する
5. iPhoneはD1に準備済みのデータを読んで表示する

完成済みの全頭診断・事前予想は、薄いライブデータで上書きしないよう保護しています。馬体重・取消・天候・馬場など分析入力が変わった時だけ、発走前に再診断します。

## GitHub Actions

| Workflow | タイミング | 役割 |
|---|---|---|
| `arvexq-prefetch.yml` | 06:30 / 08:30 / 11:30 JST、手動、関連コード更新 | 全レースの出走表・AI分析を事前生成してD1へ保存 |
| `arvexq-sync.yml` | 5分ごと（JST 7:00〜23:59）、手動、関連コード更新 | 変動データだけを軽量更新 |
| `arvexq-result-repair.yml` | Realtime Syncとずらして5分ごと、手動 | 発走済みで結果/払戻が未完のレースを古い順に補修 |
| `arvexq-history-sync.yml` | 毎時17分、手動 | 直近7日の欠損を巡回補修 |
| `arvexq-backtest.yml` | 毎日23:45 JST、手動 | 地方中心のv206バックテスト |
| `arvexq-jra-backtest.yml` | 手動 | 中央専用v208バックテスト |
| `arvexq-validation.yml` | main向けPR、main更新、手動 | 構文、PWAビルド、同期不変条件、Workflow YAMLを検証 |

D1への書き込みにはGitHub Actions Secret `SYNC_TOKEN` を使います。

## ログとキャッシュの運用

- Actions画面には原則として**件数・成功/失敗・最終指標だけ**を表示する
- 詳細ログはファイルへ出し、失敗時だけ末尾80行をActionsへ表示する
- 深掘りが必要な失敗ログは短期Artifact（3日）へ保存する
- 5分ごとのRealtime Sync / Result Repairは**新しいGitHub cacheを毎回作らない**
- SQLiteの永続cacheは主にFull Prefetch側で作り、軽量ジョブは必要に応じてread-onlyで復元する
- バックテストArtifactは14日で自動削除する

生成JSON、SQLite、ログ、研究出力は `.gitignore` で除外し、リポジトリへコミットしません。

## mainの主なファイル

```text
.
├── app.py
├── build_static.py
├── arvexq/
│   └── pipeline/
├── scripts/
│   ├── arvexq_prefetch.py
│   ├── arvexq_live_sync.py
│   ├── arvexq_result_repair.py
│   ├── arvexq_history_repair.py
│   └── arvexq_sqlite_health.py
├── backtest_v206.py
├── backtest_v208_jra.py
├── docs/audits/
├── .github/workflows/
├── requirements.txt
└── wrangler.toml
```

## ローカルで動かす

```bash
pip install -r requirements.txt
KEIBA_DATA_DIR=./.arvexq-data ARVEXQ_BOOTSTRAP_WARM=0 uvicorn app:app --port 8000
python build_static.py
```

## データ取得について

中央はJRA公式/外部競馬情報サイト、地方はNAR公式/外部競馬情報サイトを組み合わせて取得します。HTMLや配信仕様が変わると取得が壊れる可能性があるため、障害調査は `docs/audits/` に日付入りで残します。

現行の監査一覧は `docs/audits/README.md` を参照してください。
