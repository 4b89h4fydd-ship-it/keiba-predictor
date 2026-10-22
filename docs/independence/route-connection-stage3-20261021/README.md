# ARVEXQ 第3段階：既存経路を箱経由で呼び出す接続コード

**176/200項目に接続コードを記述。共有経路・部分接続を含み、全て動作未検証。残り24項目は空箱・競合・既存caller不在・独立asset/workflow入口の保留。**

## 基点と範囲

- main: `6f21f2e595df17f840c785c31a9f1c5a802bb169`
- 第1段階: `4c7bcd821fc5490d123a29c95dca17bb542de621`
- 第2段階: `a6fbf7390fead86488eaea143411957557d65d36`
- 参考PR #374: `e3485d7d0a738116cb55493475a8c72d7a54b0c8`。大型変更を取り込まない。
- branch: `connect/arvexq-200-existing-routes-stage3-20261021`

第1/第2段階の箱・割当資料だけを最新mainへ重ね、今回の接続アダプターと呼び出し変更を追加した。既存の研究候補・モデル・旧分離PRのロジックは取り込まない。mainの新規morning-picks原本も保持。

## 実際に変えた呼び出し経路

| 対象 | コード上の経路 | 保持したもの |
| --- | --- | --- |
| Pythonの既存関数/定数 | 既存caller → item_NNNの明示import alias → 同じ元オブジェクト | 元モジュール・関数・キャッシュ・値 |
| フィールドモジュール | 既存netkeiba合成 → 箱のmodule_reference → 同じ元module object | 元FIELDSの参照先・各extract本体 |
| app.pyの既存関数 | 元の公開名/HTTP登録 → 箱routes → 同じファイルのprivate原実装 | 元本文・引数/注釈・既存app decorator。wrapsで公開signatureを保持 |
| 既存SOURCE処理 | 同じinstaller/compile → 原定義＋末尾の転送wrapper → 箱routes → 元関数 | 原SOURCE literalを残し、計算本文は複写せず同じ関数を保持 |
| Worker helper | 既存import → 箱のESM re-export → 同じ元関数 | fetch/SQL/圧縮/例外本体 |
| Worker default.fetch | 既存URL/既存Worker → 箱173（webは共有145）→ 同じ既存fetch | 既存API/webのfetch本文・env/ctx/request |
| app.jsの既存関数 | 元の公開関数名/引数 → 箱の転送関数 → private原関数 | 元本文、this、arguments。新画面/予想式なし |
| UI asset読み込み | 既存compose_app_script → 各箱の固定asset loader → 既存read_asset | history/forecastの元assetと順序。転送helperのみ前置 |

Pythonの転送アダプターは元callableを明示引数として一度呼ぶだけ。JavaScriptはReflect.applyで同じreceiver/argumentsの元関数を一度呼ぶだけ。共通処理を箱の数だけ再計算しない。登録dispatcher、別API、別取得ルート、別Workerサービス、学習/予想方式は作っていない。

SOURCEの原文字列は保持し、既存installerのexec先namespaceも変更していない。app.pyの公開関数はfunctools.wrapsで元signatureを参照し、HTTP等のdecoratorは公開wrapperに保持する。HTTP decoratorの種類/引数/公開名130件は元と同じ。

既存監査CLIはmainから元auditへの1回の呼び出しだけを196経由にした。元監査判定は変更せず、CLI/テストは実行しない。

## 中央・地方と予想6系統

既存のJRA/NAR分岐・識別子・引数・返却値の本文を保持する。共有パーサーの参照共有はデータ統合を意味しない。

| 系統 | 今回の扱い |
| --- | --- |
| 能力 | 089の元ability参照を接続。現在のobserved_model/engineを変更・復活させない |
| 脚質 | 098〜104の既存共有計算の呼び出しだけ接続。印や勝率へ新たに結合しない |
| 展開 | 105の既存projection・106の既存共有処理を接続。114の空箱は埋めない |
| 確率 | 113の既存pure helper参照を接続。校正済み予想モデルを新設しない |
| 印 | 116は空の互換実装を保持。印の新規判断は接続しない。表示枠は既存原本のまま |
| おすすめ買い目 | 121/187等の既存保存原本の読み出し/表示入口を接続。新たな買い目を生成しない |

現在のengine.py/marks.py/tickets.py/observed_model.pyは元のまま。空の互換実装を勝手に稼働させず、無効化済みモデルも復活させない。

## 競合と未接続

[STATUS.md](STATUS.md)に200項目、未接続24件、部分保留15件の番号・役割・理由を記載。各箱のconnection.jsonには実際のcaller/原source/箱targetと保留箇所を記録。

進行中35PRを照合。個別変更のある元モジュールとapp.pyの該当変更関数は接続保留し、JSも#368/#213/#112が変更する関数は保留した。過去の構造案#13/#14/#16/#367および隔離案#373〜#376は比較資料として扱い、取り込まず、既存枝を一切更新しない。同じ原ファイルに対する別構造案との統合競合は残っており、勝手にmerge/rebase/cherry-pickしない。

app.py/app.jsは他PRと同じファイルだが、個別PRで変更される関数の本文は上書きしていない。既存大型構造案とは統合時の競合があり得るためDraft/DO NOT MERGEで保存する。機能の意味が変わる競合解消は今回行わない。

## 静的確認だけを実施

- Python/JS/ESMの構文とimport先/公開名、箱を含む静的依存の循環を照合。
- 接続対象のPython原本文208件、JS原本文102件、Worker既存fetch本文2件を保持。
- 元HTTP decorator130件、Python原signatureのASTを保持。
- import名不一致・検出された新規box循環・構文エラーは静的確認上0件。
- tests、workflow、HTML、CSS、SQL、TOML、保存原本の変更/削除なし。api_preserved.mjsも元のまま。

**これはテスト/動作検証ではない。** アプリimport、API/Worker/UI起動、pytest/unittest/Node smoke、PWAビルド、Actions手動起動、本番通信は行っていない。コミットは[skip ci]を付ける。接続成功/実動作成功/CI合格は認定しない。

## 保存資料

- summary.json：176/200の意味と件数
- STATUS.md：全200項目・未接続・部分保留
- 各箱connection.json：実際に書いた接続経路
- connections.json.gz / coverage.json.gz：全接続/200項目の機械可読一覧
- deferred.json / conflicts.json / ui-conflicts.json：保留・重複対象
- shared-bindings.json：単一共有接続点へのalias関係
- body-preservation.json / ui-body-preservation.json：原本文のSHA/所在
- static-structure.json / static-js-structure.json / static-contracts.json：構文・依存名・原本文等の静的照合
- open-prs.json：35PRのhead/base/変更ファイル
- changed-files.json：mainからの追加/変更ファイルの分類

第3段階の接続コード保存とPR/Issue記録で停止する。第4段階のテスト・main統合・本番デプロイには進まない。
