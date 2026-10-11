# ARVEXQ ドメイン分離：調査・段階移行報告

基準main: `c025fea65f95aa0641b1c674ef703e4644b9b3a3`。専用ブランチ: `refactor/arvexq-domain-separation`。

このPRは安全な初期3段階の実装。全体の構造改革は未完了。依存のない計算・解析を実際のPython/JavaScriptモジュールへ移し、状態を持つ取得・保存・画面の残作業を明示する。mainの直接更新・本番デプロイ・既存の発走前アーカイブの再生成は行っていない。

## 調査対象と証拠

- [変更前の全ファイル台帳](inventory-main.json)：mainの全追跡ファイル、サイズ、行数、ハッシュ、Python import・参照名、JavaScript関数・require、設定のパス参照。
- [変更後の台帳](inventory.json)：同じ方法で取得。ローカルDBと生成済みdistはソース台帳に含めない。
- [Python関数の移動表](extracted-functions.json)：98関数について移動元・移動先・本体と引数のASTハッシュ。
- [JavaScript関数の移動表](extracted-js-functions.json)：31関数について移動元・移動先・原文ハッシュ。
- `python scripts/arvexq_structure_inventory.py --output /tmp/inventory.json` で再調査できる。

台帳の`domain_hint`はパスからの分類候補。混在ファイルの最終的な責任分割は下表で判断する。Python参照名は静的候補であり、すべてが外部依存ではない。文字列SOURCEを実行する既存3インストーラも展開して調査している。JavaScriptのDOMイベント・動的呼び出しは静的な名前列挙だけでは解決しない。

## 大分類・中分類・小分類・必要な第4階層

既存の実体があるフォルダ名を維持し、責任で8ドメインに対応付ける。まだ実装しない分類の空フォルダは作らない。

| 大分類 | 中分類 | 小分類／第4階層 | 実在する主要ファイル |
|---|---|---|---|
| データ管理 | 取得・提供元 | 中央／地方／許諾フィード／履歴補完 | `databanks/{jra,nar,nar_official_csv,authorized_feeds,netkeiba_career}.py`, `ingest/{orchestrator,fallback_enrichment,full_career}.py` |
| データ管理 | 解析 | NARアーカイブ／払戻・オッズ／補完セル | `ingest/parsers/{nar_archive,market,supplemental}.py` **新規** |
| データ管理 | 履歴 | 全走の結合／中央レース行の変換 | `ingest/history/{run_merge,central_rows}.py` **新規** |
| データ管理 | 正規化 | 文字・数値／馬体重・斤量／中央フィード | `normalize/{scalars,measurements,central_feed}.py` **新規**、`normalize/race.py` |
| データ管理 | 保存・輸送 | スナップショット／キャリア輸送／圧縮 | `ingest/{full_snapshot_codec,career_transport}.py`, `infra/{race_stores,legacy_stores}.py` |
| データ分析 | 全キャリア | 取得証拠／欠損／走歴の分析 | `career_analysis.py`, `career_missing.py`, `horse_detail.py`, `prediction/{career_profile,career_evidence,career_readiness}.py` |
| データ分析 | 特徴量 | 全走の指標／窓・条件別の集計 | `features/mass/run_metrics.py` **新規**、`prediction/mass_feature_factory.py` |
| データ分析 | 検証 | 確率計算／指標／時系列校正／研究 | `backtest/probability_metrics.py` **新規**、`backtest/{metrics,ticket_metrics,factor_weight_calibration}.py`, `prediction/{research_shadow,research_evaluation}.py` |
| 予想ロジック | 主モデル | 能力／因子／複数ヘッド／印 | `prediction/{ability,factor_model,multi_head,final_marks,honmei_gate}.py` |
| 予想ロジック | 過去走の計算 | 脚質／上がり／条件適合 | `prediction/metrics/past_runs.py` **新規** |
| 予想ロジック | 旧モデル | 共通／勝ち馬／役割特徴／コース／専門モデル／戦術／役割出力／因子 | `prediction/legacy/{common,winner,role_features,course,professional,tactical,role_utilities,factors}.py` **新規** |
| 予想ロジック | ブラウザモデル | 展開・隊列／相対評価 | `ui/static/prediction/{pace_simulation,relative_grades}.js` **新規** |
| 予想ロジック | 発走前固定 | 予想・履歴・固定時刻の保持 | `prediction/prerace_archive.py`、`app.py`の固定処理、`app.js`の印固定処理 **後者は残存** |
| 厳選レース | 適格性 | 選考スナップショット／学習 | `selection/{race_selector,race_selectability,race_selectability_snapshot,race_selectability_training}.py` |
| 厳選レース | 朝の選定 | 入力方針／レーン判定／確定選考／固定証拠 | `pipeline/morning_input_policy.js`, `ui/static/morning/{ticket_lane_classifier,selection_cut,selected_race_pipeline,frozen_ticket_evidence,saved_ticket_receipt}.js` |
| 特別予想 | 独自判定 | メイン／重賞／高知ファイナル | `ui/static/morning/special_selection.js`（既存の独立判定を維持） |
| 特別予想 | 表示・履歴 | 朝の対象固定／詳細計画の描画 | `app.js`の`specialForecastRaceCandidates`等 **残存** |
| 買い目 | 独立戦略 | 本線／3連単／保険／軸なし | `ui/static/betting/{main_strategy,trifecta_strategy,insurance_strategy,no_axis_strategy}.js` |
| 買い目 | 生成・判定 | 入力準備／軸ゲート／3系統統合 | `betting/{bet_readiness,podium_axis_guard,three_way_engine,legacy_v213_order_model}.js`, `arvexq/betting/trifecta.py` |
| 買い目 | 表示・固定 | 表示モジュール／朝の領収書／発走前固定 | `betting/bet_view.js`, `morning/saved_ticket_receipt.js`、`app.js`の生成アダプタと固定処理 **一部残存** |
| アプリ画面 | 画面・スタイル | トップ／レース／詳細／研究ビュー | `ui/static/{index.html,styles.css,app.js}`, `styles/*.css`, `research/*.js` |
| アプリ画面 | 資産・配信 | 共通構成表／Python配信／Node読込 | `ui/static/app_sources.json`, `ui/app_source.cjs` **新規**、`ui/assets.py`, `build_static.py` |
| システム基盤 | 保存状態・監視 | 準備状態／確定結果／固定情報を保つ行結合 | `infra/snapshot_status.py` **新規**、`infra/{live_delta_guard,pure_snapshots}.py`, `observability/timing.py` |
| システム基盤 | API・設定・運用 | FastAPI／Worker／設定／GitHub Actions | `app.py`, `workers/api_preserved.mjs`, `config/settings.py`, `.github/workflows/*.yml`, `scripts/*.py` |

パスは特記がなければ`arvexq/`からの相対パス。分類一覧は責任を示し、同じ予想判定を8つの別実装へ複製するものではない。

## 実施順序と移動対応

1. **段階1・実施済み**：`app.py`の通信・DBに依存しない54関数を12モジュールへ移動。既存呼び出し名はimportとして維持。
2. **段階2・実施済み**：旧モデル19関数を8モジュールへ移動。特徴量生成25関数を`features/mass/run_metrics.py`へ移動。旧バージョン定数2個は`tactical.py`を所有元とし、旧名前空間にもimportする。
3. **段階3・実施済み**：`app.js`の展開22関数・相対評価9関数を2モジュールへ移動。各モジュールは`create(deps)`で依存する純粋な関数を受け取り、計算APIを返す。ブラウザstate、localStorage、fetchを直接参照しない。
4. **段階4・未実施**：取得を提供元・用途別に移す。状態・キャッシュ・ロック・スレッド・公式情報の優先順位を明示的なサービスへ移行。各提供元の失敗隔離を維持する。
5. **段階5・未実施**：保存をスナップショット・全キャリア・朝の履歴・発走前固定に分ける。DBのトランザクション、上書き禁止、read-after-write確認を維持する。
6. **段階6・未実施**：APIと画面を機能別に移す。ルート、イベント、画面stateを明示化し、独立した厳選・特別・買い目の判定を共有オーケストレータで取り扱う。
7. **段階7・未実施**：CSS・Worker・バックテスト・運用スクリプトを責任単位で分離。トップのDOMとCSSの描画結果を比較してから移す。

| 移動前 | 移動後 | 内容 |
|---|---|---|
| `app.py` | `normalize/scalars.py`, `normalize/measurements.py`, `normalize/central_feed.py` | 値の変換・正規化 |
| `app.py` | `ingest/parsers/{nar_archive,market,supplemental}.py` | 取得済み入力の解析 |
| `app.py` | `ingest/history/{run_merge,central_rows}.py`, `ingest/scheduling.py` | 履歴結合・変換・対象期間計算 |
| `app.py` | `prediction/metrics/past_runs.py`, `backtest/probability_metrics.py` | 指標・確率評価 |
| `app.py` | `infra/snapshot_status.py` | 状態確認・既存カード保持 |
| `domain/legacy_evaluation.py:SOURCE` | `prediction/legacy/*.py` | 状態を持たない旧モデル計算 |
| `prediction/mass_feature_factory.py` | `features/mass/run_metrics.py` | 過去走からの基本指標・統計 |
| `ui/static/app.js` | `ui/static/prediction/{pace_simulation,relative_grades}.js` | 展開の計算・回路別の相対評価 |
| 各ツールの直接`app.js`読込 | `ui/app_source.cjs`／`ui/assets.py` | 同一構成表からの読込 |

関数名単位の完全な移動対応は2つの移動表JSONを参照。ファイル全体の移動はなく、既存importの互換性を維持している。

## 共通データ・インターフェース

現段階では互換性を優先し、既存辞書のキー・値・引数・戻り値を維持する。強制的な新型への変換や欠損値の補完は追加しない。

- Race: `id`, `date`, `circuit`, `track`, `raceNumber`, `surface`, `distance`, `horses`。
- Horse: `horseNumber`, `name`, `allPastRuns`（全キャリア）、`recentRaces`（表示・特定指標の既存窓）。全キャリアの取得・分析を5走へ変換しない。
- Run: `date`, `track`, `distance`, `finish`, `fieldSize`, `cornerPositions`, `timeSeconds`, 情報源・取得証拠。既存の用途ごとの窓・重みを維持する。
- Frozen artifacts: 既存の`preRacePrediction`, `predictionAudit`, 買い目と朝のアーカイブの時刻・ハッシュを保持。今回のfixture生成は合成入力のみ。
- JS純粋計算API: `ARVEXQPaceSimulation.create({n,clamp,mean,courseProfile,courseTraits,firstTurnDistance})`、`ARVEXQRelativeGrades.create({n,clamp,mean,raceMode,recentFinishScore})`。
- 資産: `app_sources.json`の順序で純粋モジュールを先に、画面アダプタを最後に結合。ブラウザ、FastAPI、静的ビルド、朝の発行、買い目captureとテストで同じソースを使う。外部ビルド依存は追加していない。

完全な型付きDTO、保存層のインターフェース、画面stateの分離は未完了。形式的な型の追加だけで統一済みとはしない。

## 巨大ファイルと残存依存

| ファイル | main | 分離後 | 判定・残作業 |
|---|---:|---:|---|
| `app.py` | 7,282 | 6,441 | 取得、固定、キャッシュ、API、バックグラウンド処理が残る。最優先 |
| `ui/static/app.js` | 5,262 | 4,910 | state、DOM、キャッシュ、厳選・特別・買い目アダプタ、印固定が残る。最優先 |
| `domain/legacy_evaluation.py` | 1,242 | 719 | 800行未満。ranker、SQLiteへのアクセス、appグローバル依存のSOURCE実行が残る |
| `prediction/mass_feature_factory.py` | 510 | 362 | 500行未満。窓別・条件別集計を所有 |
| `ui/static/styles/race_v222_plus.css` | 2,247 | 2,247 | UI責任ごとに分離する対象。トップデザイン維持が先決 |
| `ui/static/styles/legacy_v118_v221.css` | 1,285 | 1,285 | 旧スタイルの使用状況を画面別に確認する |
| `ui/static/styles.css` | 1,150 | 1,150 | トップ・共通スタイルの境界が残る |
| `workers/api_preserved.mjs` | 1,131 | 1,131 | D1・保護項目・API別の分離が必要 |
| `backtest_v206.py` | 710 | 710 | CLIと評価・データ読込の責任を検査済み、移動は次段階 |
| `scripts/arvexq_live_sync.py` | 695 | 695 | merge／送信／検証を分離する対象。保護項目と再試行を保持する |
| `infra/race_stores.py` | 546 | 546 | 2種類のストアと旧namespace依存を分離する対象 |
| `infra/legacy_stores.py` | 525 | 525 | NARパーサ・NARストア・中央ストアのnamespace依存が残る |
| `scripts/arvexq_prefetch.py` | 514 | 514 | 取得・分析の準備・保存・配信を独立させる対象 |

今回の新規計算モジュールはすべて500行未満。`__init__.py`は実装のあるパッケージのimport境界であり、将来用の空ドメインフォルダは作成していない。

残る重要な依存は、`app.py`に注入する3インストーラ、グローバルストアとスレッドロック、`app.js`のstateと関数宣言の順序、WorkerのD1契約、patch系スクリプトの旧ソース構造への依存。動的グローバル参照を保つだけの新しいexec分割は追加していない。旧インストーラには抽出後の実モジュールをimportする短い橋渡しだけを追加した。

## 検証

詳しい最終結果は[検証記録](validation.md)。式だけの検査に加え、変更前mainで生成した中央・地方・新馬・障害の合成入力の出力と比較する。fixtureは評価精度の証明ではなく、リファクタリングによる差異の検出に用いる。

統合前に残存する巨大ファイルと移行範囲をレビューすること。この初期PRを全体分離完了として扱わない。
