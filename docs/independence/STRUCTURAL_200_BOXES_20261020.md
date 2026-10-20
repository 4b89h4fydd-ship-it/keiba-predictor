# 200項目の箱・既存処理の配置（2026-10-20）

200項目すべての箱を先に作成し、既存実装の配置と動作確認をまとめて実施する方式へ変更。PR #367 の開発ブランチのみ。本番完了件数とは別の構造上の進捗。

## 実装

- 全200件に `arvexq/components/item_NNN/` と名前・区分・所有ソース・共有依存を記した `component.json` を作成。未割当の箱はない。
- `app.py` の228関数/クラスの実体を52箱へ移動。定義位置で `install_component` を呼び、元のグローバル変数・ロック・保存先・デコレータを保って既存経路へ接続する。すでに `infra/legacy_stores.py` 等でも使われている互換実行方式の延長。これは共有実行状態の完全解消を意味しない。
- 既存の38解析モジュールに加え、専任ソース24モジュールを箱へ移動（計96モジュール）。従来のインポート先は同一実装オブジェクトを返す互換窓口として保持。相対インポートは元の依存先を絶対指定する。
- UI組立の103処理断片を箱へ移動。残る324断片を共有UIとして明示。追加の独立スクリプト7件も責務箱から同一バイトで組み立てる。`ui-assembly.json` の順序で全断片を組み立て、生成済み `app.js` とバイト単位で一致する場合だけ使用する。移動元に存在した末尾空白や空行もUI断片には維持する。デザインを変更しない。
- 対応元のみを登録していた79箱のうち23箱で専任Pythonモジュールの実体を移動し、旧インポート経路と同一実装を指す互換窓口を保持した。残り11箱は対応元の登録段階。移動済みの箱にも呼び出し元や共通処理への依存が残り、完全独立化や本番検証の完了とは扱わない。
- 仕様待ち29箱は空。既存の16個の旧予想補助定義は隔離したままで、新しい箱から委譲・実行しない。v3中央/地方の12予想モジュールは引き続き `None` を返す。
- 保存済み観測データは複製・改変せず、元の保存場所を読む。D1/SQLiteスキーマ・取得URL・キャッシュ条件・UI・本番環境を変更しない。

## 分離漏れ検出と検証

`python scripts/arvexq_components_audit.py` で全200ID/項目名、配置元の実在、所有関数の重複、未割当、予想空箱の汚染、244定義すべてのAST一致、UIの完全一致を検証する。構造上の割当を本番認定に読み替えない。
`tests/test_components_200.py` は全箱の無副作用インポート、所有権拒否、不正ID拒否、コピーされた台帳の不変性、予想空箱、API127経路のメソッド・名前・シグネチャ一致も検証する。既存のソース契約テストは実体を組み立てた `composed_app_source()` を参照するよう更新し、検証対象の関数本体を省略しない。

## 2026-10-20 追加の構造移動（GitHub上の旧実装から再実施）

以前の作業環境に残った未コミット変更は取得できないため、GitHub上の開発ブランチを元に23箱・24既存Pythonモジュールを移動した。公開モジュール名は sys.modules により新しい箱内の実体へ接続し、従来のインポート文を変更しない。相対インポートは元の絶対パスに明示して同じ依存先を参照する。保存データ・取得先・表示・予想ロジック・本番環境は触れない。対応元のみの箱は11。構造検証と本番認定を混同しない。

### キャッシュポリシー分離の限定範囲

#146 `factual_cache_key` は箱へ移動し、#161 `freshness` も別の箱に分離した。既存の `arvexq.v3.transport.cache` は互換的に両関数を公開し続ける。#146 は保存/読込/削除のストア実体を所有しておらず、共通 `race_detail_key` と現行保存経路に依存するため、**結果キャッシュの完全独立化を認定しない**。両関数は保存済みデータの変更、TTLの既定値追加、キャッシュ破棄を実施しない。

### #075 コーナー通過順位の追加分離

旧 `arvexq.ingest.corner_order` の実体を #075 の箱に移動し、旧モジュール名は同じ実装オブジェクトへ接続する。既存の文字列正規化ヘルパーへの共有依存を台帳に残し、完全独立とは認定しない。

### 追加: レース番号・読込HTTP再試行・個別UI5資産

#011 の既存JRAレース番号関数、#160 の既存 `get_json` 実体を責務箱へ移動。両方とも共通ファイルを保つため移動済み共有依存であり完全独立ではない。#058/#182/#185/#186/#187 は既存UIスクリプトと同一の本体を責務箱に置き、`read_asset` が同一バイト検証後に責務箱の版を組み立てに使用する。旧静的ファイルは既存の配信先を壊さない互換スナップショットとして保存し、表示内容は変更しない。実データの改変、新取得経路、予想ロジック有効化はしない。

### 結果・払戻を責務別に分岐（10箱を追加接続）

#070〜#072の着順/着差/時計、および#077〜#083の券種別払戻は、従来の `result_facts.py` の汎用抽出本体から責務箱の読み取り実装に切り出した。#075の通過順位、#076の単勝払戻も同じ呼出境界に接続した。既存のJRA/NAR別読み取りモジュールは公開関数経由で同じキー/値と欠損扱いを返す。対象は**保存済み結果の読み取り投影**のみであり、#076の共通払戻HTMLパーサ、保存・修復・確定判定・本番UIなどの完全分離を主張しない。予想・買い目生成は実施しない。

### app.js 既存21断片の所有先移動

オッズ表示(#068)、発走前保存(#125)、メインレース(#130)、重賞(#131)、高知ファイナル(#132)、レース選定(#133)、厳選レース買い目表示(#136)、固定スナップショット表示(#147)、開催場別レース一覧(#178)、出馬表(#180)へ**既存共有UIの21断片を元のGit blobのまま**移動。UI組立台帳 `ui-assembly.json` の順序とSHA256は保持し、配列の `path` と `owner` のみ更新した。旧共有UIの所有済み断片ファイルは削除し、同じblob SHAを各責務箱に配置する。生成 `app.js` のバイト列は変わらない設計。各断片のグローバル依存、旧アルゴリズム由来の共有状態、ビルド・ライブ検証は残存するので**独立化・本番検証済みとは扱わない**。予想ロジックを新しく生成・有効化していない。

### 追加の既存Python実体移動（#063/#084/#109/#128）

JRA既存オッズパーサとコース速度参照テーブルは完全一致の互換インポートで責務箱へ移した。結果行マージ処理は共通のオッズマージ関数から切り出したが、詳細オブジェクトの同一インメモリ状態を更新する仕様は維持した。中央地方区分の静的正規化辞書と純関数を責務箱に移した。既存予想ロジック、印、買い目、保存先、取得経路は変更しない。

### 追加の既存分離（#074/#175/#196）

速報・暫定ラベル条件、HTTP再試行／既存表示フォールバックのステータス判定、200箱監査の実体を箱に移動し、従来の公開関数とCLIを保持。共有された確定処理、D1通信、既存CIランナーは未独立。オッズ・取得URL・予想ロジック・本番環境の変更はない。

### #134・#137の既存読込UI資産を責務箱へ移動

既存の `morning/saved_ticket_receipt.js` と `previous_ai_results.js` はそれぞれ#134/#137へ同一バイトで配置。既存のURL/保存先はそのまま維持し、資産の読込補助関数 `read_asset` が元ファイルとの完全一致を検証して所有先から読み取る。ただし直接配信する旧静的URLおよび#138の当日成績は共有のままであり、完全独立や実際の本番動作確認を示さない。発走前買い目の新規作成・再計算は行わない。

### 追加5箱：キャッシュキー・版管理・NAR取得処理

#143/#144 は既存のレース詳細キーと履歴キーの純関数本体、#148 は既存スナップショットの版番号と復元許容条件を責務箱へ分離。これらはストア全体の独立化やスキーマ変更ではなく、元のキー生成結果と圧縮復元を保持する。#156 NAR公式出馬表の観測値パーサ、#158 NAR公式当日変更情報の既存読込処理を互換エイリアス付きで移動。旧URL/再試行/更新条件を追加・変更せず、保存済みデータを編集しない。完全独立化・本番検証は未完了。

### #150 手動復旧Workflowの実体移動

既存のGitHub Actions手動復旧ワークフローにあった「既存原本の検証付き書き出し」と「検証原本のみをコミットする」二つのコマンド列を `item_150/scripts/` に実体移動し、元のWorkflowから同じ順序・環境変数で実行するよう接続。旧Workflowの `workflow_dispatch` とキャッシュ取得・出力パス・主ブランチpushの挙動は変えない。**今回の作業でワークフローは起動せず、main push・復旧・本番更新は行わない。** GitHub Actionsと保護対象の保存データは依然として共有依存するため、完全独立ではない。

### 既存Worker/D1/オッズ4箱の実体移動

#139の全量スナップショット管理、#145の既存オッズ実取得、#173のAPI/Web Worker入口を責務箱へ移し、元のWorkerパスはES Module互換re-exportを保持。#174はD1環境バインディングの既存関数を#139から再公開。既存HTTP APIとWorker設定は変えず、予想生成も実施しない。Workerのバンドル/デプロイCIが未確認で、共有依存が残るため完全独立と認定しない。

### 脚質率5項目の保存済み観測値境界

#098〜#102は既存の`styleRates`/`runningStyleRates` にすでに格納された数値を読み取る純関数を作成。欠損は `None` を返す。これは各馬の過去走から脚質率を計算する実装ではなく、既存予想にも接続していない。**脚質率算出の完全独立化は未完了**。既存の印・買い目を変更しない。

### 最終配置: #138 当日成績 / #199 Cloudflare配備検証境界

#138に既存当日成績のUI処理7断片を元のblobのまま移し、公開UIの順序・内容を保持する。#199は既存2件のCloudflareデプロイワークフローを**読取専用**で検査する境界を所有する。Workflow自体は従来のGitHub Actions配置を維持し、デプロイは実行していない。**200箱の構造上の配置済みと、完全独立/本番検証済みは異なる**。脚質率の過去走からの計算や保存処理の完全切断も未完了。

### D1所有境界の実体移動（#174）

既存の`rewriteDetailSQL`と`storageEnvironment`の実装を#139から#174へ実体移動。既存呼び出し名はre-exportで維持し、SQL書換規則・DB構造・取得経路を一文字も変更しない。実D1との疎通と本番接続の認定は別途必要。

### #145 オッズキャッシュ実体の切出し

公開Worker内の既存キャッシュ参照・15秒レスポンスおよび7日保持バックアップの書込・取得関数を#145専用モジュールに切り出し。`caches.default`と`ctx.waitUntil`は既存Runtimeを利用する。キャッシュキー、TTL、強制更新、失敗時の保存済み値参照は不変。新規予想機能や新規取得先は増やさない。

### #145 既存キャッシュキーの責務境界

Workerの通常オッズ・最終保存オッズの2つのキー生成を既存 `Request` 構築式のまま専任箱へ移動。URL文字列・強制更新・TTL・読取保存条件は不変。新しい取得経路は設けない。

## 全項目の配置

状態: `migrated-module`=既存Pythonモジュール実体移動、`migrated-shared-context`=実体移動/既存共有状態で接続、`migrated-ui-fragment`=画面ソース実体移動、`mapped-existing-source`=既存ファイルとの対応を確定、`reserved`=仕様待ちの空箱。

| ID | 項目 | 箱 | 配置状態 |
|---:|---|---|---|
| 001 | NAR天候解析 | [item_001](../../arvexq/components/item_001/component.json) | migrated-module |
| 002 | NAR馬場状態解析 | [item_002](../../arvexq/components/item_002/component.json) | migrated-module |
| 003 | NAR出走取消・除外解析 | [item_003](../../arvexq/components/item_003/component.json) | migrated-module |
| 004 | JRA天候解析 | [item_004](../../arvexq/components/item_004/component.json) | migrated-module |
| 005 | JRA芝馬場状態解析 | [item_005](../../arvexq/components/item_005/component.json) | migrated-module |
| 006 | JRAダート馬場状態解析 | [item_006](../../arvexq/components/item_006/component.json) | migrated-module |
| 007 | JRA障害コース馬場状態判定 | [item_007](../../arvexq/components/item_007/component.json) | migrated-module |
| 008 | 開催日取得 | [item_008](../../arvexq/components/item_008/component.json) | migrated-shared-context |
| 009 | 開催場取得 | [item_009](../../arvexq/components/item_009/component.json) | migrated-shared-context |
| 010 | 開催日程取得 | [item_010](../../arvexq/components/item_010/component.json) | migrated-shared-context |
| 011 | レース番号取得 | [item_011](../../arvexq/components/item_011/component.json) | migrated-shared-context |
| 012 | レース名取得 | [item_012](../../arvexq/components/item_012/component.json) | migrated-module |
| 013 | グレード・クラス取得 | [item_013](../../arvexq/components/item_013/component.json) | migrated-module |
| 014 | 発走時刻取得 | [item_014](../../arvexq/components/item_014/component.json) | migrated-module |
| 015 | 芝・ダート・障害区分取得 | [item_015](../../arvexq/components/item_015/component.json) | migrated-module |
| 016 | 距離取得 | [item_016](../../arvexq/components/item_016/component.json) | migrated-module |
| 017 | コース情報取得 | [item_017](../../arvexq/components/item_017/component.json) | migrated-module |
| 018 | 出走頭数取得 | [item_018](../../arvexq/components/item_018/component.json) | migrated-module |
| 019 | 賞金情報取得 | [item_019](../../arvexq/components/item_019/component.json) | migrated-module |
| 020 | JRA公式データ解析 | [item_020](../../arvexq/components/item_020/component.json) | migrated-shared-context |
| 021 | NAR公式データ解析 | [item_021](../../arvexq/components/item_021/component.json) | migrated-shared-context |
| 022 | 外部競馬サイトデータ解析 | [item_022](../../arvexq/components/item_022/component.json) | migrated-shared-context |
| 023 | レースID照合 | [item_023](../../arvexq/components/item_023/component.json) | migrated-module |
| 024 | 重複レース統合 | [item_024](../../arvexq/components/item_024/component.json) | migrated-module |
| 025 | 馬番 | [item_025](../../arvexq/components/item_025/component.json) | migrated-shared-context |
| 026 | 枠番 | [item_026](../../arvexq/components/item_026/component.json) | migrated-module |
| 027 | 馬名 | [item_027](../../arvexq/components/item_027/component.json) | migrated-module |
| 028 | 性別 | [item_028](../../arvexq/components/item_028/component.json) | migrated-module |
| 029 | 年齢 | [item_029](../../arvexq/components/item_029/component.json) | migrated-module |
| 030 | 斤量 | [item_030](../../arvexq/components/item_030/component.json) | migrated-module |
| 031 | 騎手 | [item_031](../../arvexq/components/item_031/component.json) | migrated-module |
| 032 | 調教師 | [item_032](../../arvexq/components/item_032/component.json) | migrated-module |
| 033 | 所属 | [item_033](../../arvexq/components/item_033/component.json) | migrated-module |
| 034 | 馬体重 | [item_034](../../arvexq/components/item_034/component.json) | migrated-module |
| 035 | 馬体重増減 | [item_035](../../arvexq/components/item_035/component.json) | migrated-module |
| 036 | 出走取消状態 | [item_036](../../arvexq/components/item_036/component.json) | migrated-module |
| 037 | 競走除外状態 | [item_037](../../arvexq/components/item_037/component.json) | migrated-module |
| 038 | 出馬表更新 | [item_038](../../arvexq/components/item_038/component.json) | migrated-shared-context |
| 039 | 馬名・馬番照合 | [item_039](../../arvexq/components/item_039/component.json) | migrated-module |
| 040 | 欠損値補完 | [item_040](../../arvexq/components/item_040/component.json) | migrated-shared-context |
| 041 | データ取得元照合 | [item_041](../../arvexq/components/item_041/component.json) | migrated-module |
| 042 | 過去走日付 | [item_042](../../arvexq/components/item_042/component.json) | migrated-shared-context |
| 043 | 過去走競馬場 | [item_043](../../arvexq/components/item_043/component.json) | migrated-module |
| 044 | 過去走距離 | [item_044](../../arvexq/components/item_044/component.json) | migrated-module |
| 045 | 過去走馬場状態 | [item_045](../../arvexq/components/item_045/component.json) | migrated-module |
| 046 | 過去走クラス | [item_046](../../arvexq/components/item_046/component.json) | migrated-module |
| 047 | 過去走着順 | [item_047](../../arvexq/components/item_047/component.json) | migrated-module |
| 048 | 過去走走破時計 | [item_048](../../arvexq/components/item_048/component.json) | migrated-module |
| 049 | 過去走着差 | [item_049](../../arvexq/components/item_049/component.json) | migrated-module |
| 050 | 過去走通過順位 | [item_050](../../arvexq/components/item_050/component.json) | migrated-module |
| 051 | 過去走上がり情報 | [item_051](../../arvexq/components/item_051/component.json) | migrated-module |
| 052 | 過去走斤量 | [item_052](../../arvexq/components/item_052/component.json) | migrated-module |
| 053 | 過去走騎手 | [item_053](../../arvexq/components/item_053/component.json) | migrated-module |
| 054 | 過去走出走頭数 | [item_054](../../arvexq/components/item_054/component.json) | migrated-module |
| 055 | 過去走重複排除 | [item_055](../../arvexq/components/item_055/component.json) | migrated-shared-context |
| 056 | JRA・NAR転入転出判別 | [item_056](../../arvexq/components/item_056/component.json) | migrated-module |
| 057 | 全競走履歴取得・補修 | [item_057](../../arvexq/components/item_057/component.json) | migrated-shared-context |
| 058 | 未来結果混入防止 | [item_058](../../arvexq/components/item_058/component.json) | migrated-ui-fragment |
| 059 | 単勝オッズ | [item_059](../../arvexq/components/item_059/component.json) | migrated-module |
| 060 | 複勝オッズ | [item_060](../../arvexq/components/item_060/component.json) | migrated-module |
| 061 | 人気順位 | [item_061](../../arvexq/components/item_061/component.json) | migrated-module |
| 062 | オッズ取得時刻 | [item_062](../../arvexq/components/item_062/component.json) | migrated-module |
| 063 | JRAオッズ解析 | [item_063](../../arvexq/components/item_063/component.json) | migrated-module |
| 064 | NARオッズ解析 | [item_064](../../arvexq/components/item_064/component.json) | migrated-shared-context |
| 065 | 外部サイトオッズ解析 | [item_065](../../arvexq/components/item_065/component.json) | migrated-shared-context |
| 066 | オッズ差分更新 | [item_066](../../arvexq/components/item_066/component.json) | migrated-shared-context |
| 067 | オッズ保存・復元 | [item_067](../../arvexq/components/item_067/component.json) | migrated-shared-context |
| 068 | オッズ表示 | [item_068](../../arvexq/components/item_068/component.json) | migrated-ui-fragment |
| 069 | オッズ欠損判定 | [item_069](../../arvexq/components/item_069/component.json) | migrated-module |
| 070 | 着順取得 | [item_070](../../arvexq/components/item_070/component.json) | migrated-shared-context |
| 071 | 着差取得 | [item_071](../../arvexq/components/item_071/component.json) | migrated-shared-context |
| 072 | 走破時計取得 | [item_072](../../arvexq/components/item_072/component.json) | migrated-shared-context |
| 073 | 確定結果判定 | [item_073](../../arvexq/components/item_073/component.json) | migrated-module |
| 074 | 速報結果判定 | [item_074](../../arvexq/components/item_074/component.json) | migrated-shared-context |
| 075 | コーナー通過順位取得 | [item_075](../../arvexq/components/item_075/component.json) | migrated-module |
| 076 | 単勝払戻 | [item_076](../../arvexq/components/item_076/component.json) | migrated-module |
| 077 | 複勝払戻 | [item_077](../../arvexq/components/item_077/component.json) | migrated-shared-context |
| 078 | 枠連払戻 | [item_078](../../arvexq/components/item_078/component.json) | migrated-shared-context |
| 079 | 馬連払戻 | [item_079](../../arvexq/components/item_079/component.json) | migrated-shared-context |
| 080 | ワイド払戻 | [item_080](../../arvexq/components/item_080/component.json) | migrated-shared-context |
| 081 | 馬単払戻 | [item_081](../../arvexq/components/item_081/component.json) | migrated-shared-context |
| 082 | 3連複払戻 | [item_082](../../arvexq/components/item_082/component.json) | migrated-shared-context |
| 083 | 3連単払戻 | [item_083](../../arvexq/components/item_083/component.json) | migrated-shared-context |
| 084 | 結果欠損補修 | [item_084](../../arvexq/components/item_084/component.json) | migrated-shared-context |
| 085 | 払戻欠損補修 | [item_085](../../arvexq/components/item_085/component.json) | migrated-shared-context |
| 086 | 確定結果上書き防止 | [item_086](../../arvexq/components/item_086/component.json) | migrated-shared-context |
| 087 | データ完全性評価 | [item_087](../../arvexq/components/item_087/component.json) | migrated-shared-context |
| 088 | 近走成績評価 | [item_088](../../arvexq/components/item_088/component.json) | reserved |
| 089 | 能力評価 | [item_089](../../arvexq/components/item_089/component.json) | reserved |
| 090 | クラス適性 | [item_090](../../arvexq/components/item_090/component.json) | reserved |
| 091 | 距離適性 | [item_091](../../arvexq/components/item_091/component.json) | reserved |
| 092 | 競馬場適性 | [item_092](../../arvexq/components/item_092/component.json) | reserved |
| 093 | コース適性 | [item_093](../../arvexq/components/item_093/component.json) | reserved |
| 094 | 馬場適性 | [item_094](../../arvexq/components/item_094/component.json) | reserved |
| 095 | 季節適性 | [item_095](../../arvexq/components/item_095/component.json) | reserved |
| 096 | 走破時計評価 | [item_096](../../arvexq/components/item_096/component.json) | reserved |
| 097 | 上がり性能評価 | [item_097](../../arvexq/components/item_097/component.json) | reserved |
| 098 | 逃げ率 | [item_098](../../arvexq/components/item_098/component.json) | migrated-shared-context |
| 099 | 先行率 | [item_099](../../arvexq/components/item_099/component.json) | migrated-shared-context |
| 100 | 差し率 | [item_100](../../arvexq/components/item_100/component.json) | migrated-shared-context |
| 101 | 追込率 | [item_101](../../arvexq/components/item_101/component.json) | migrated-shared-context |
| 102 | 下がり率 | [item_102](../../arvexq/components/item_102/component.json) | migrated-shared-context |
| 103 | 脚質点 | [item_103](../../arvexq/components/item_103/component.json) | reserved |
| 104 | 位置取り評価 | [item_104](../../arvexq/components/item_104/component.json) | reserved |
| 105 | 展開・ペース分析 | [item_105](../../arvexq/components/item_105/component.json) | reserved |
| 106 | 先行争い分析 | [item_106](../../arvexq/components/item_106/component.json) | reserved |
| 107 | 騎手・調教師情報評価 | [item_107](../../arvexq/components/item_107/component.json) | reserved |
| 108 | 馬体重・斤量影響分析 | [item_108](../../arvexq/components/item_108/component.json) | reserved |
| 109 | コース別スピード基準 | [item_109](../../arvexq/components/item_109/component.json) | migrated-module |
| 110 | 全頭診断結果保存・表示 | [item_110](../../arvexq/components/item_110/component.json) | migrated-shared-context |
| 111 | 予想入力データ | [item_111](../../arvexq/components/item_111/component.json) | migrated-module |
| 112 | 予想ロジック | [item_112](../../arvexq/components/item_112/component.json) | reserved |
| 113 | 勝率・順位確率計算 | [item_113](../../arvexq/components/item_113/component.json) | reserved |
| 114 | 展開シミュレーション | [item_114](../../arvexq/components/item_114/component.json) | reserved |
| 115 | 予想信頼度判定 | [item_115](../../arvexq/components/item_115/component.json) | reserved |
| 116 | 印生成 | [item_116](../../arvexq/components/item_116/component.json) | reserved |
| 117 | ◎【単】判定 | [item_117](../../arvexq/components/item_117/component.json) | reserved |
| 118 | ◎【軸】判定 | [item_118](../../arvexq/components/item_118/component.json) | reserved |
| 119 | その他の印判定 | [item_119](../../arvexq/components/item_119/component.json) | reserved |
| 120 | A・B・C評価 | [item_120](../../arvexq/components/item_120/component.json) | reserved |
| 121 | 買い目生成 | [item_121](../../arvexq/components/item_121/component.json) | reserved |
| 122 | 本線買い目 | [item_122](../../arvexq/components/item_122/component.json) | reserved |
| 123 | 3連単チャレンジ | [item_123](../../arvexq/components/item_123/component.json) | reserved |
| 124 | 買い目点数・配分 | [item_124](../../arvexq/components/item_124/component.json) | reserved |
| 125 | 発走前の予想・買い目保存 | [item_125](../../arvexq/components/item_125/component.json) | migrated-ui-fragment |
| 126 | 予想・印・買い目画面表示 | [item_126](../../arvexq/components/item_126/component.json) | migrated-module |
| 127 | 的中判定・成績検証 | [item_127](../../arvexq/components/item_127/component.json) | migrated-shared-context |
| 128 | 中央・地方開催区分 | [item_128](../../arvexq/components/item_128/component.json) | migrated-module |
| 129 | 本日の厳選レース | [item_129](../../arvexq/components/item_129/component.json) | migrated-shared-context |
| 130 | メインレース | [item_130](../../arvexq/components/item_130/component.json) | migrated-ui-fragment |
| 131 | 重賞レース | [item_131](../../arvexq/components/item_131/component.json) | migrated-ui-fragment |
| 132 | 高知ファイナル | [item_132](../../arvexq/components/item_132/component.json) | migrated-ui-fragment |
| 133 | レース選定条件 | [item_133](../../arvexq/components/item_133/component.json) | migrated-ui-fragment |
| 134 | レース選定結果保存 | [item_134](../../arvexq/components/item_134/component.json) | migrated-ui-fragment |
| 135 | 事前選定・発走後区別 | [item_135](../../arvexq/components/item_135/component.json) | migrated-shared-context |
| 136 | 厳選レース買い目表示 | [item_136](../../arvexq/components/item_136/component.json) | migrated-ui-fragment |
| 137 | 前日予想成績 | [item_137](../../arvexq/components/item_137/component.json) | migrated-ui-fragment |
| 138 | 当日予想成績 | [item_138](../../arvexq/components/item_138/component.json) | migrated-ui-fragment |
| 139 | D1保存 | [item_139](../../arvexq/components/item_139/component.json) | migrated-shared-context |
| 140 | SQLite保存 | [item_140](../../arvexq/components/item_140/component.json) | migrated-shared-context |
| 141 | レース一覧キャッシュ | [item_141](../../arvexq/components/item_141/component.json) | migrated-shared-context |
| 142 | レース詳細キャッシュ | [item_142](../../arvexq/components/item_142/component.json) | migrated-shared-context |
| 143 | 出馬表キャッシュ | [item_143](../../arvexq/components/item_143/component.json) | migrated-shared-context |
| 144 | 過去走キャッシュ | [item_144](../../arvexq/components/item_144/component.json) | migrated-shared-context |
| 145 | オッズキャッシュ | [item_145](../../arvexq/components/item_145/component.json) | migrated-shared-context |
| 146 | 結果キャッシュ | [item_146](../../arvexq/components/item_146/component.json) | migrated-module |
| 147 | 発走前スナップショット | [item_147](../../arvexq/components/item_147/component.json) | migrated-ui-fragment |
| 148 | 保存データバージョン管理 | [item_148](../../arvexq/components/item_148/component.json) | migrated-shared-context |
| 149 | キャッシュ期限・破棄 | [item_149](../../arvexq/components/item_149/component.json) | migrated-shared-context |
| 150 | 保存失敗時復旧 | [item_150](../../arvexq/components/item_150/component.json) | migrated-shared-context |
| 151 | Full Prefetch | [item_151](../../arvexq/components/item_151/component.json) | migrated-shared-context |
| 152 | Realtime Sync | [item_152](../../arvexq/components/item_152/component.json) | migrated-shared-context |
| 153 | Result Repair | [item_153](../../arvexq/components/item_153/component.json) | migrated-shared-context |
| 154 | History Repair | [item_154](../../arvexq/components/item_154/component.json) | migrated-shared-context |
| 155 | オッズ自動更新 | [item_155](../../arvexq/components/item_155/component.json) | migrated-shared-context |
| 156 | 馬体重自動更新 | [item_156](../../arvexq/components/item_156/component.json) | migrated-module |
| 157 | 天候・馬場自動更新 | [item_157](../../arvexq/components/item_157/component.json) | migrated-shared-context |
| 158 | 取消・除外自動更新 | [item_158](../../arvexq/components/item_158/component.json) | migrated-module |
| 159 | レース詳細事前生成 | [item_159](../../arvexq/components/item_159/component.json) | migrated-shared-context |
| 160 | 取得失敗時再試行 | [item_160](../../arvexq/components/item_160/component.json) | migrated-shared-context |
| 161 | データ鮮度判定 | [item_161](../../arvexq/components/item_161/component.json) | migrated-module |
| 162 | 同期状態・エラー管理 | [item_162](../../arvexq/components/item_162/component.json) | migrated-shared-context |
| 163 | レース一覧API | [item_163](../../arvexq/components/item_163/component.json) | migrated-shared-context |
| 164 | レース詳細API | [item_164](../../arvexq/components/item_164/component.json) | migrated-shared-context |
| 165 | 馬別情報API | [item_165](../../arvexq/components/item_165/component.json) | migrated-shared-context |
| 166 | 過去走API | [item_166](../../arvexq/components/item_166/component.json) | migrated-shared-context |
| 167 | オッズ更新API | [item_167](../../arvexq/components/item_167/component.json) | migrated-shared-context |
| 168 | 払戻API | [item_168](../../arvexq/components/item_168/component.json) | migrated-shared-context |
| 169 | 環境情報API | [item_169](../../arvexq/components/item_169/component.json) | migrated-shared-context |
| 170 | 全頭診断API | [item_170](../../arvexq/components/item_170/component.json) | migrated-shared-context |
| 171 | 保存状態API | [item_171](../../arvexq/components/item_171/component.json) | migrated-shared-context |
| 172 | ヘルスチェックAPI | [item_172](../../arvexq/components/item_172/component.json) | migrated-shared-context |
| 173 | Cloudflare Worker | [item_173](../../arvexq/components/item_173/component.json) | migrated-shared-context |
| 174 | D1接続 | [item_174](../../arvexq/components/item_174/component.json) | migrated-shared-context |
| 175 | APIエラー処理 | [item_175](../../arvexq/components/item_175/component.json) | migrated-shared-context |
| 176 | ホーム画面 | [item_176](../../arvexq/components/item_176/component.json) | migrated-shared-context |
| 177 | 開催場一覧 | [item_177](../../arvexq/components/item_177/component.json) | migrated-ui-fragment |
| 178 | 開催場別レース一覧 | [item_178](../../arvexq/components/item_178/component.json) | migrated-ui-fragment |
| 179 | レース詳細 | [item_179](../../arvexq/components/item_179/component.json) | migrated-shared-context |
| 180 | 出馬表 | [item_180](../../arvexq/components/item_180/component.json) | migrated-ui-fragment |
| 181 | 馬別詳細 | [item_181](../../arvexq/components/item_181/component.json) | migrated-ui-fragment |
| 182 | 過去走表示 | [item_182](../../arvexq/components/item_182/component.json) | migrated-ui-fragment |
| 183 | 脚質マップ | [item_183](../../arvexq/components/item_183/component.json) | migrated-ui-fragment |
| 184 | 展開予想表示 | [item_184](../../arvexq/components/item_184/component.json) | migrated-ui-fragment |
| 185 | 予想表示枠 | [item_185](../../arvexq/components/item_185/component.json) | migrated-ui-fragment |
| 186 | 印表示枠 | [item_186](../../arvexq/components/item_186/component.json) | migrated-ui-fragment |
| 187 | 買い目表示枠 | [item_187](../../arvexq/components/item_187/component.json) | migrated-ui-fragment |
| 188 | 結果・払戻表示 | [item_188](../../arvexq/components/item_188/component.json) | migrated-ui-fragment |
| 189 | リアルタイム表示 | [item_189](../../arvexq/components/item_189/component.json) | migrated-ui-fragment |
| 190 | お気に入り | [item_190](../../arvexq/components/item_190/component.json) | migrated-ui-fragment |
| 191 | 画面遷移・戻る操作 | [item_191](../../arvexq/components/item_191/component.json) | migrated-ui-fragment |
| 192 | 手動更新・プル更新 | [item_192](../../arvexq/components/item_192/component.json) | migrated-ui-fragment |
| 193 | PWA・ホーム画面起動 | [item_193](../../arvexq/components/item_193/component.json) | migrated-shared-context |
| 194 | オフライン・キャッシュ表示 | [item_194](../../arvexq/components/item_194/component.json) | migrated-ui-fragment |
| 195 | CSS・レイアウト管理 | [item_195](../../arvexq/components/item_195/component.json) | migrated-shared-context |
| 196 | Python・JavaScript自動テスト | [item_196](../../arvexq/components/item_196/component.json) | migrated-shared-context |
| 197 | JRA・NARデータ検証とバックテスト | [item_197](../../arvexq/components/item_197/component.json) | migrated-shared-context |
| 198 | GitHub Actions CI・PWAビルド | [item_198](../../arvexq/components/item_198/component.json) | migrated-shared-context |
| 199 | Cloudflareデプロイ・本番動作確認 | [item_199](../../arvexq/components/item_199/component.json) | migrated-shared-context |
| 200 | ログ・障害監視 | [item_200](../../arvexq/components/item_200/component.json) | migrated-shared-context |

## 残る完全独立化

79箱の参照元について責務別の実体移動を続けること、共有appグローバルと共有UIヘルパーを明示的な引数へ縮小すること、および本番の保存/キャッシュ/API/UIの十観点確認は残る。今回の「200箱あり・既存ソース割当済み」は「200項目の完全独立/本番検証済み」と同義ではない。

## 実行結果

- 全体Pythonテスト: **1,167 passed**, 37 subtests passed（12件は既存FastAPI非推奨警告）。
- 最終追加契約: `tests/test_components_200.py` **15 passed**。
- 既存API **127経路** のメソッド・名前・引数シグネチャが移動前後で一致。
- 固定 **244定義** のAST（引数・本体・デコレータ）が一致。所有関数228件の重複なし。
- 構造監査: **200箱・割当未解決0・エラー0**。
- `python build_static.py` と `node --check dist/app-v330.js` 成功。
- production-boundaries / design-freeze のNodeスモーク成功。
- 本番完了認定は従来の3件から変更しない。CIは反映後のGitHub Actionsで別途確認する。


### 2026-10-20 #008 / #011 JRA識別子責務の接続・構造監査強化

- 既存の `_jra_date_from_cname` 本体を #008 の専任 `jra_date.py` へ移し、従来の `arvexq.ingest.jra_identifiers` は同一関数オブジェクトを再公開。#011 のレース番号関数も従来どおり再公開する。既存のID形式・暦日妥当性・異常時の空値・参照箇所は不変。
- #008 と #011 の所有回路を実体に合わせて JRA のみに訂正。#008 の中央レース正規化は依然 `app.py` 共通ヘルパーに依存し、完全独立とは認定しない。
- #196 の監査が所有資産の実在・箱外参照および構造台帳との状態不一致を検出するよう強化。構造監査結果は本番十観点検証と区別する。
- 既存画面・API・データ取得先・保存/キャッシュ・予想処理・本番への変更はない。CI結果は対象コミットに対するGitHub Actionsを確認してから記録する。

### #009〜#019 JRAフィールド専用回路の台帳訂正（2026-10-20）

#009/#010/#012〜#019 の実際の既存呼び出し元を中央JRA専用とし、`component.json` の `circuits` を JRA のみに訂正。先行修正した #008/#011 と元から専用の #020 を合わせ、#008〜#020 の13責務は既存 JRA 呼び出しだけを示す。NAR側の別パーサ・取得経路・出力は変更しない。JRA/NAR両経路の実運用データ漏洩防止は別途十観点検証が必要。監査対象となる所有回路の誤表示を防ぐメタデータ回帰テストを追加した。既存の画面、コードロジック、保存、キャッシュ、予想、CI設定は変更していない。

### 全200箱の実体保有検査（2026-10-20）

構造監査 #196 は、仕様待ち29箱への所有コード/資産/スクリプト混入を拒否することに加え、仕様待ち**以外**の箱が実体を1件も持たず参照先だけ登録した場合をエラーにする。既存の共有状態82箱は全件に少なくとも一つの実体配置を確認した。ただし「所有コードまたは資産がある」ことは完全独立化を意味しない。保存、キャッシュ、API、UI、JRA/NARの十観点検証と本番読戻しは引き続き未完了。


### #009 / #010 既存JRA開催場・日程解析の責務箱実体移動（2026-10-20）

- `arvexq.ingest.race_fields.track` の既存関数本体を変更せず #009 `track.py` へ移し、旧import先は同じモジュール実体の互換窓口とする。コードから存在しない開催場を補完しない。
- `arvexq.ingest.race_fields.meeting_schedule` の既存関数本体を変更せず #010 `meeting_schedule.py` へ移し、旧import先は同じモジュール実体の互換窓口とする。日程未掲載時は既存と同様のゼロ/空文字を返す。
- #009/#010 の共有アプリ呼び出しは元の `install_component` 位置で維持。特に #010 の共有キャッシュ・HTTP・TTL・出力は変更せず依存を台帳へ追記した。両箱とも `migrated-shared-context` に据え置き、完全独立・本番検証済としない。
- 旧/新import先の同一オブジェクト、既存入力と欠損時の挙動を回帰テスト化。総owned_modulesの構造期待値は98から100となる。UI/API/取得経路/保存/予想29空箱/デプロイは不変。


### #042〜#055 過去走JRA専任責務の境界訂正と暦日検証（2026-10-20）

#042〜#054の所有実体はJRA専任の過去走観測値抽出器、#055の所有定義は `_jra_merge_runs` / `_jra_merge_run_fields`。各箱の `circuits` 表示を実体に合わせて `["JRA"]` に訂正。JRA出走馬の地方開催過去走を読むことと、NAR取得処理を所有することは別。NAR側の取得・補修・保存・UIを変更しない。#042/#055の既存共有依存を台帳へ追記。

#042 `extract_date` は同じJRA公式日付文字列パターンを読み、存在しない日付・非閏年の2月29日を `None` とする。既存 `parse_jra_history_cell` はその場合に行を返さない。閏年正常値と発走日以降の除外も回帰テストに追加した。取得URL・保存先・キャッシュ・UI・予想方式は変更しない。

#057は14の既存JRA/NAR履歴定義を旧アプリ共有文脈に接続しており、`RACEDB` / `NarStore` / `PREPARED_STORE` / HTTPとロックの共有依存を明記した。既存混合ディスパッチの不明区分拒否は未認定。保存・キャッシュ・API・画面・本番読戻しの十観点検証が不足するため、いずれも完全独立や本番完了とは認定しない。


### 2026-10-20 P0-3 結果払戻レポートの観測範囲（開発のみ）

既存の `result_state` は `bool(payouts)` を修復完了の運用判定に使用しているが、1件以上の払戻は発売された全券種の完全取得を証明しない。既存の再取得条件・回数・保存ペイロード・速報配信は変更せず、`scripts/arvexq_result_repair.py` の既存監査レポートに `payout_observations` を追記。券種は既存 `PAYOUT_KINDS` を参照し、行数、認識できる券種、未識別ラベル、不正行、競走不成立状態、運用上の旧判定を分けて表示する。

`offeredKindsVerified=false`、`completePayoutCoverageVerified=false` を明示する。発売券種の公式一覧は今回の入力にないため、全8券種を発売済と仮定せず、未掲載券種を必ず欠損と判定しない。既存レポート以外の取得・DB・UI・予想経路は変更しない。本番D1読戻しや全券種完備の確認は実施していない。


### 2026-10-20 P0-1 NAR同名馬・既存SQLite対公式CSVの読取専用再現

`legacy_bridge.audit_nar_store_history(conn,horse,cutoff,official_archive)` は既存接続のSELECTのみで、旧 `NarStore.recent_races` と同じ厳密馬名・対象日前条件を使い、`finish>0` 前後の行数を比較。既存 `NarOfficialArchive.by_name` を使ってレース日・競馬場・R番号・当該レース馬番と公式生年月日を照合し、理由内訳を `official-birth-date-compatible` / `conflicting-official-birth-date` / `unverified-*` / `excluded-by-legacy-finish-filter` として出力する。恒久馬IDの照合完了ではなく、未収録アーカイブは欠落確定としない。

合成公式ZIPと旧SQLiteスキーマによる回帰テストで旧検索が同名・別生年月日馬の陽性着順レコードを返すリスクを再現し、除外理由・アーカイブ未収録の扱い・読取前後の保存行数不変を検証する。実混在件数は元SQLiteと元公式ZIP双方が必要なため未算出。既存の `NarStore.recent_races` / `_nar_store_adapters` の出力・取得経路・DBスキーマ・保存先・UI・予想は不変。個体識別の本番仕様は未承認のため変更しない。


### 2026-10-20 P0-1監査SQLの結合条件精密化

読取り監査 `audit_nar_store_history` で、既存 `NarStore.recent_races` の `entries JOIN races` を厳密に計上するよう `LEFT JOIN` で監査対象を抽出する。実際の検索に入らない `entries` の孤立行を `excluded-by-legacy-race-join` として分離。新フィールド `dbNameDateRowsBeforeJoin` は馬名・日付での全行、`dbRowsBeforeLegacyFinishFilter` は親レースに結合できる行、`legacyPositiveRows` は結合可能かつ `finish>0` の行を表す。無効着順と本人不一致は別理由。合成SQLiteの孤立行を追加した回帰テストで旧`recent_races`の検索件数と監査陽性件数の一致、監査前後の保存行数不変を検証する。本番SQLiteや公式原本の実混入件数についての証明には使わない。


### 2026-10-20 P0-2 第64段階・過去走欠損と保存済み原本の別経路照合（オフライン）

同日研究記録 `docs/research/stage64-results/official_gap_recheck.json` の **NAR 11R・34頭** と、同リポジトリの `arvexq/ui/static/racecards/2026-10-16.json` および `arvexq/ui/static/saved-snapshots/2026-10-16.json` から参照される11個の圧縮保存原本を照合した。保存原本は既存の `snapshot_digest._restore` によるSHA-256・サイズ検証付きで復元し、馬番・馬名が34頭すべてで一致。保存原本の `recentRaces` / `allPastRuns` の直接観測件数は **33頭が(0,0)、川崎3R・2番アークブレイブが(3,3)** であり、公式供給アーカイブの調査結果「34頭で有効な過去走なし」と同じ概念ではない。後者1頭には保存済み履歴があるが、取得元、個体照合、全生涯網羅性は当該直接保存数から確定しない。

`tests/test_v3_snapshot_digest.py` に上記の静的原本照合を回帰検証として追加し、原本を編集せず検証可能にした。**現時点の本番D1は読んでいない**。取得元応答、統合前後、D1/API/UIの時系列照合がないため、33頭の初回欠損箇所・無出走判定・表示欠損判定は未確定。公式アーカイブ取得先、原本、保存先、200項目、予想29空箱に変更なし。


### 2026-10-20 P0-2 第64段階保存原本の初出走フラグ監査

既存のSHA-256検証付き `snapshot_digest._restore` でNAR 2026-10-16の研究対象11R・34頭を読み直す回帰テストを拡張。直接保存の過去走0件の33頭に対して、`career_transport.recover_horse` でも有効な過去走が復元できないことと、`runner_gaps.classify_absent_prior` が初出走を確定しないことを検証する。**33頭中18頭には `debutNoHistory=True` が保存されているが、これは公的に確認された初出走を意味しない。** この33頭の保存履歴監査状態は `missing` であり、公式出走回数の本人照合を証明しない。川崎3R・2番アークブレイブの直接保存3走は既存の照合結果どおり保持する。

P0-2における欠損工程の断定には、取得元応答、公式馬ID/生年月日、解析除外、統合前後、SQLite・D1・API・UIの各時点の同一馬データが必要。今回はGitHubの保存原本と研究レポートの同一静的資料のみを使い、外部取得・本番D1読戻しを行わない。実際のデビュー数、欠損の最初の工程、保存中の同名馬混在数は**未認定**。既存の予想・取得・UI・保存・200箱構造を変更しない。


### 2026-10-20 P0-2 33頭の保存済み履歴取得監査レシート・厳密化

既存保存原本 2026-10-16 NAR 11R/34頭から、直接過去走0件の **33頭** に限定し、`_careerHistoryAudit` の値をSHA-256検証済みの同一保存原本で確認した。33頭すべてが `fetchAttempted=True`、`providersAttempted=["nar_official","nar_official_past_results","netkeiba_verified_career"]`、`failedProviders=[]`、`failedEvidenceProviders=[]`、`requestedAtRaceDate="2026-10-16"`、`reportedStarts=None`、`status="missing"` だった。**試行済みでエラー記録がないことは、レスポンスが有効だった・本人照合に成功した・公式過去走がなかったことの証明ではない**。提供元の応答件数、照合で除外した行、解析前後件数、永続DB/D1読戻しはまだ測定されていない。

`tests/test_v3_snapshot_digest.py` の実保存レース照合テストの弱い `0 <= fetchAttempted <= 33` を厳密な事実記録へ更新し、試行対象3件・失敗記録・公式通算出走回数未証明・対象日を別々に回帰検証。**既存の取得先、処理順、保存原本、UI、予想ロジック、200箱構造は一切変更しない**。生年月日同名馬の実混入数および33頭の初回欠損工程は本番・原本照合がないため未確定のまま。
