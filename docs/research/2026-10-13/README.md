# ARVEXQ 統合研究・実証監査（2026-10-13）

## 結論と完成判定

**新予測エンジンの本番採用条件は満たされていない。完成とは判定しない。**
保存原本を使う実験では、補正候補の勝ち馬捕捉はわずかに上昇したが、確率損失と3頭捕捉は悪化した。候補を採用せず、現行予測・既存UI・原本を維持する。今回実装したのは研究評価基盤、研究用の整合順位分布、および学習データ分割の根本修正である。

確認したmain: `66c8c9f660784f54b8264cfa1591dd447fa2cbae`。
最新mainのコードと保存当時の予測は区別する。保存ロックのモデル名は `evidence-v317-consensus-rebuild` 等で、mainの `arvexq-true-run-pure-sectional-45-35-20-v2` と一致しない。古いバージョン定数が残る経路もあり、**以下の成績を最新mainの実測精度として使ってはならない**。

## 実際に測定した結果

ソースは既存GitHub Actions [run 38418202882](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38418202882)、artifact `11824149666` の7日分API応答。日次API自体のレース件数との一致を確認した。公式全開催との独立照合は未実施。取得元システムの「確定」を採用し、競走主催者との二重照合は未実施。

| 対象 | 件数・期間 |
|---|---|
| 日次APIレース | 396、2026-10-07〜13 |
| 発走前の封印済みロック | 237 |
| 一意の1〜3着と確率を照合できるレース | 235 |
| 封印なしの除外 | 159 |
| 重複順位等により上位3頭を一意に評価できない除外 | 2 |
| 学習期間 | 10/07〜09、54レース |
| 候補選定期間 | 10/10〜11、73レース |
| 後期評価期間 | 10/12〜13、108レース |

後期108レースでの同一レース比較:

| 指標 | 保存当時のdecisionProbability | 保存P1の補正候補 |
|---|---:|---:|
| 勝率1位馬の1着 | 30/108、27.78% | 31/108、28.70% |
| 上記Wilson 95%区間 | 20.21〜36.88% | 21.02〜37.85% |
| 勝ち馬上位2頭捕捉 | 45.37% | 44.44% |
| 勝ち馬上位3頭捕捉 | 56.48% | 55.56% |
| レース単位の勝者Log Loss | 2.11266 | 2.14669 |
| レース単位の多クラスBrier（頭数で割らない） | 0.83641 | 0.84742 |

候補は `p_i ∝ savedP1_i^0.75`。各headの指数を学習期間で選び、headを選定期間のLog Lossで選んだ。後期ラベルをパラメータ探索には使用していない。Log Loss差（候補−基準）は `+0.03403`、レース単位2,000回bootstrapの95%区間 `[-0.01688, +0.08418]`。改善は証明されず、不採用。

ただし監査中、封印時計がcaptureより約1秒早い既存仕様を発見し、適格条件を「captureとsealがともに発走前」に修正して再集計した。旧・新適格条件の成績を閲覧しているため、この後期期間は完全な事前登録済み最終テストではない。候補採用には別の未閲覧期間が必要。同日の相関、モデルの変更、少数開催、季節偏りも残る。

均等確率のLog Lossは後期で2.38662。ただし同率馬の順位を馬番で決めた捕捉率には予測上の意味がなく、人気順との比較の代用にはしない。

## データ品質上の重大な発見

- 保存静的ファイル272件の内訳は、268原本＋4日次索引。268原本すべてでSHA256、内容長、ファイル名の一致を確認。期間は10/10〜13、3,044頭。変更件数0。
- その268原本では結果あり3件、買い目あり2件、封印済み7件。これらは朝等の保存時点の状態であり、現在D1全体の保存率ではない。
- 現行raw collectorで測った近走着順軸の欠損は221/3,044（7.26%）。上がり**順位／percentile**軸は3,044/3,044（100%）欠損。上がり時計の存在と順位情報の存在を混同しない。固定20%項が中立値に置換され、区間情報が順位に寄与しないケースがこの集合では全件。
- 266件のmass特徴スナップショットに `capturedAtEpoch` は0件。hashだけで発走前の存在は証明できない。これらからCatBoostを学習して実証済みと扱うことはしなかった。
- 235件の古いロック中49件で、少なくとも1頭の `P1+P2+P3 > 1`。各順位列の和が1でも、同一馬の相互排他的順位の和が1を超えることは許されない。これは保存当時の確率の不整合であり、最新mainのPL式に同じ問題があると断定しない。
- 89件で `sealedAtEpoch < capturedAtEpoch`。両時計は発走前だが監査性に問題がある。過去原本は訂正しない。
- [最新日次監査 run 38425634703](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/38425634703) は58開催レース、52封印、6未封印、52件の買い目不足（48 capture-failed、4 missing）、有効買い目0を報告。予想保存と買い目保存は別の問題。取得済みday原本の48件のcaptureErrorは、削除済み podium_axis_guard.js を読む旧captureのENOENTを記録している。現行mainのcaptureはその依存を既に撤去しているため、同じ修正を重ねない。発走後の失敗原本を成功買い目に作り替えない。
- 旧v206バックテストの評価0件の原因は「結果が存在しない」ことではない。成果物の396件には結果があり、軽量day応答の馬には `integratedEvaluation` が0件。`race_from_detail` が全馬を除外していた。新監査は保存済みロックを直接読む。軽量応答から事後の評価を復元しない。

## 成果物の場所と状態

| 要求された成果物 | 提供物・状態 |
|---|---|
| 1 世界理論研究 | [research.md](research.md)。一次資料の比較。世界全予想家・全論文の網羅は未完了 |
| 2 根本原理 | [design.md](design.md) の因果構造。実測可能／潜在／不明を分離 |
| 3 採用・除外・保留一覧 | design.md。精度への独立寄与は未確定 |
| 4 最終モデル設計 | design.md。候補設計、採用済みとは扱わない |
| 5 近走5走仕様 | design.md。既存の観測処理と研究候補を区別 |
| 6 展開仕様 | design.md。統一シナリオ分布の仕様、展開推定器は未学習 |
| 7 印・買い目仕様 | design.md。実測校正なしのA/B/C閾値は未決定 |
| 8 バックテスト | [measurements.json](measurements.json)、本ページ。235件の保存確率評価 |
| 9 新旧比較 | 本ページ。最新mainを同時点で再現した全面新旧比較は未完了 |
| 10 実装・テスト | [execution.md](execution.md) |
| 11 Cloudflare検証 | execution.md。直接認証なし。初回day取得403、後続health/versionは200を確認。公開サイトの全面確認未完了 |
| 12 最終結論 | 本ページ、design.mdの12項目。確定不能な項目は暫定 |

## 再現

```bash
python -m pip install -r requirements.txt pytest
# GitHub artifact 11824149666 のZIPを手元に保全し、raw/を展開する。
# 元データの再公開許諾は未確認。ZIPはworkspace内のresearch-outputに保存し、公開repoへ追加しない。
PYTHONPATH=. python scripts/arvexq_integrated_research.py \
  --result-dir research-output/integrated-20261013/existing/raw \
  --out docs/research/2026-10-13/measurements.json
python -m unittest discover -s tests -p 'test_mass_temporal_split.py'
python -m unittest discover -s tests -p 'test_integrated_research.py'
python -m unittest discover -s tests -p 'test_research_rank_distribution.py'
```

入力7ファイルのSHA256と268原本のmanifestをmeasurements.jsonへ保存。Actions artifactは期限付きで、期限切れ後の取得は保証できない。取得済みZIPは `/workspace/keiba-predictor/research-output/integrated-20261013/existing-backtest.zip` に保全。独立校正コードは標準ライブラリのみ。所要時間はmeasurements.jsonに記録し、推論速度と混同しない。

最優先は、新モデル追加よりも**現行バージョンの発走前入力・順位分布・買い目・取得時計の完全な同時保存**。その上で未閲覧の長期間を評価し、中央／地方／特殊条件の悪化がないことを確認する。80%以上の的中率、回収率改善、本番完成は報告しない。

品質検証: 全pytest 322件＋12subtests PASS。既存取得系のsandbox timeoutは子プロセスEPERMを切り分け、許可済み制約外実行で完走。既存Node smoke計7件とv330 PWAビルドPASS。直接本番readはHTML・API health・version・10/13の58race summaryが200。実iPhoneでの全機能・長期精度は未検証。
