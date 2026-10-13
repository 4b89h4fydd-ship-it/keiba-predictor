# 実装・権限・検証台帳

## 権限確認

- GitHub connectorで対象repoのpull/push/admin権限を確認。作業前mainは `66c8c9f660784f54b8264cfa1591dd447fa2cbae`。branch protectionの応答はprotected=falseだが、既存Validation CIを通す方針を維持。
- 管理環境はPython 3.12.14、Node v24.19.0。専用venvに既存requirementsが入り、MLのnumpy/sklearn/catboostは未導入。235件の低次元補正は標準ライブラリで完結。
- 環境statusのsecret／outbound identityは空。Cloudflareの直接認証は利用できない。GitHub Actionsの既存デプロイではCloudflare認証確認が成功しているため、アカウント自体に認証がないとは断定しない。
- `/etc/codex/network-policy.json` を確認。VPNなし、HTTP unrestrictedの設定、API readiness policy状態はunknown。通常のproxyを使用し、403を迂回しない。
- 初回Cloudflare day APIへの直接GETは403。後続のhealthとversion.jsonは200を確認。GitHub connectorでユーザーの既存Actions成果物を取得して代替評価を実施。第三者の制限回避、ログイン、データ新規購入は行っていない。
- JRA-VAN等の新規データ契約・再配布許諾は未確認。ライセンス不明データを新規scrapeしない。取得済みActions ZIPはworkspace内で保全し、公開repoへ再公開しない。

## 変更1: 学習／調整／評価の同日分割

原因: `mass_training_dataset.split_walk_forward` はraceIdの並びを比率で切るため、1日20raceでも3群を作る。また文字列raceIdの順が開催時刻とは限らず、同日の将来raceがTRAINに入り得る。

修正: ISO日付／raceIdを検査し、race内日付矛盾を拒否。日付blockで3期間を分離。3日未満はholdoutを空にして既存train_headの不足gateで停止。比率の不正を拒否。関数名は互換維持するが、反復walk-forwardであるとは記述しない。

影響: 研究用mass-model trainingの分割。実際の発走前score／印／買い目には接続されない。データ不足で以前は学習できた入力が停止するのは意図した検証保護。

変更前の4テストは全てFAIL、修正後は全てPASS。`scripts/check_mass_training_store.py` はPASS。
追跡commit: `a65a81ee3d7a25b36b27c46091454013d6c8bf21`。

## 変更2: 保存原本のoffline評価

- `scripts/arvexq_integrated_research.py`: envelope SHA256／byte length監査、発走前frozen gate、確定resultとのrace単位join、重複／同着／欠損／invalid probability除外、保存モデルのloss／Brier／捕捉率／校正／Wilson区間、日付分離の補正実験、paired bootstrap、保存印実績、失敗race台帳。
- rawの事後馬データ・最終オッズ・事後scoreを予測特徴に使わない。欠損／不整合分布は正規化して隠さない。保存丸め誤差だけを調整。
- `tests/test_integrated_research.py`: postoff・unfrozen・同着除外、final odds／scoreが特徴にならないこと、原本不変、invalid vectorが拒否されること。
- `docs/research/2026-10-13/measurements.json`:実測235race、入力7ファイルhash、268原本manifest、実験結果と除外理由。下記報告書とともに保存。

## 変更3: 研究用joint順位分布

- `arvexq/research/rank_distribution.py`: 全着順marginalのexact subset DP、ordered podium joint、scenario mixture、6券種のevent-union。
- `tests/test_research_rank_distribution.py`: brute-forceの独立全順序列挙との一致、全馬／全順位の和、uniformの券種確率、重複ワイドのunion、未知／取消ID・NaN・0・少頭数、scenarioの不正を検査。
- **数学的検証のみ。calibrated=false。現行予測にimportしていない。** 任意の架空能力指標、scenario発生確率、A/B/C閾値は追加しない。
- `probability-benchmark.json`: 合成strengthの一回測定。18頭約1.57秒、最大整合誤差1e-15未満。実raceの速度精度／Cloudflare性能とは区別。

## 変更4: CIと研究文書

Validation workflowに新12テストと修復した既存2テストを独立stepとして追加。既存の検証step、deploy方式、許可、保護を撤去していない。

README／research／design／executionと2つの実測JSONを保存。予測部分の旧ロジック削除0件。本番候補不採用のため、旧ロジックに加点する変更も0件。UI／トップ／ロゴ／配色の変更0件。保存原本・買い目・結果の変更0件。

## ローカル検証結果

| 検証 | 結果 |
|---|---|
| 関連unit suite（新12件＋既存36件） | 48 PASS、2.792秒 |
| three_factor_parity smoke | PASS |
| visible_honmei smoke | PASS |
| frozen_marks smoke | PASS |
| mark_lock smoke | PASS |
| full_snapshot smoke | PASS |
| capture_three_factor smoke | PASS（子プロセスEPERMのため許可済み制約外で実行） |
| course_capture_dependency smoke | PASS |
| Python syntax、git diff --check | PASS |
| build_static.py | PASS、v330、83files |
| 全unit一括discover | 180秒timeout、exit124。既存AuthorizedHistoryRuntimeTests付近で止まり完走せず。今回変更が原因と断定せず、全通過とはしない |
| 制約外全pytest（依存導入・旧テスト修復後） | 322 PASS、12 subtests PASS、15.58秒、既存DeprecationWarning等12件 |
| 学習済み新AI精度 | 未検証、候補補正は不採用 |
| 実iPhone Safari/PWA、全中央・全地方raceの操作 | 未実施 |
| 現行／新方式の同時点全面比較、長期ROI、DD、展開精度 | 未測定 |

ローカルログ: `research-output/integrated-20261013/`。全unit一括実行の失敗を隠すために既存テストを削除しない。

## GitHub／Cloudflare

変更は `codex/arvexq-integrated-research-20261013` に追跡可能なcommitで提出し、既存Validationの結果でmain統合を判断する。最終PR／統合SHA／CI結果は本タスクの最終回答とPRのchecksに記録する。CI失敗時にmainを直接動かして迂回しない。

既存mainの [Web Deploy run 38410741613](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38410741613) はsuccess。認証確認・deploy・production HTML／version・当日racecard・morning archive確認stepまで成功をconnectorで確認した。これは本タスクの新エンジンを反映した証拠ではない。

本番予測・配信assetsに変更がないため、新しい予測方式のCloudflareデプロイは行わない。直接readの測定はproduction-read.jsonに記録。直接デプロイ認証なし、実iPhone未検証を残存制約として報告する。

## 最終品質監査18項目

| 項目 | 判定 |
|---|---|
| 研究の実装反映 | 評価分離・原本評価・確率計算試作へ反映。新本番AIへは未反映 |
| 採用モデルが検証済みか | 新採用なし。現行性能の独立確証なし |
| 古い／重複予測経路なし | 未達。Python/UI・軸別score・legacy呼出経路を記録 |
| 同一raceの競合予測なし | 未確証。原本保護testはPASS |
| 勝率和100% | 235保存vectorはPASS。全本番race未監査 |
| 着順整合 | 古い235件中49件はpodium和でFAIL。研究試作は数学的PASS |
| 印と確率一致 | 現行軸別scoreなど未適合を記録。新仕様未採用 |
| 買い目同一分布 | 現行PL式と研究試作を確認。券種実測校正未完 |
| 展開と最終予測統一 | 未達、scenario learner未学習 |
| 発走前原本保存 | 静的268SHA検証。日次監査58件に6件未封印 |
| 結果で原本変化なし | 関連unitとsmoke PASS。全D1不変性の独立照合未実施 |
| 取消／除外 | 既存smoke・研究invalid ID PASS、全live race未確認 |
| 新馬／障害 | 仕様を候補設計へ記録、独立精度未測定 |
| 欠損 | 明示・研究gateあり、区間順位100%欠損を未解決 |
| 速度 | exact合成分布のみ測定、全race/UI改善未測定 |
| main統合 | PRとCIの結果に依存、最終回答で状態報告 |
| Cloudflare新方式反映 | 未実施、候補不採用 |
| 本番正常性 | 既存deploy CIの成功を確認、全面実機検証未実施 |

本タスクの直接本番read: API health=200（ok=true）、PWA version.json=200（build=v330、shell=three-factor-authoritative、model=v317-consensus-rebuild）。version内model名の現行方式との不一致も残る。HTML／当日summaryのread測定はproduction-read.jsonを参照。HTTP応答時間は一回のネットワーク測定で、画面描画時間ではない。

保存買い目失敗の追加原因調査: 10/13の48failed receiptに、旧captureが削除済みbetting/podium_axis_guard.jsを読むENOENTが記録されていた。現行mainはこの依存を既に撤去済み。過去原本は修正しない。現行captureの既存smokeはPASS。通常sandboxでは簡単なNode子プロセスでもEPERMとなることを再現し、許可済みの制約外実行で確認した。

## 変更5: 古い発走前表示テストの修復

制約外の全unittestは315件中、既存test_prepost_mark_consistencyの古い文字列期待とpytest依存不足の2件が失敗。pytestをテスト環境へ導入。古いテストは、現行コードに対して既存arvexq_frozen_marks_smokeを実行するbehavior regressionへ変更した。発走前の最新印、発走後の保存印、原本不変を実際に検査する。既存UIは変更せず、古い朝原本を発走前表示へ上書きする仕様を復活させない。全pytestは322件＋12subtests PASS（15.58秒）。旧文字列assertを削除して対象仕様を無検査にせず、実挙動の検査へ置換した。
