# 国内外の理論と一次資料比較

調査日2026-10-13。確認済み公開説明、学術モデル、今回の実測を分離する。非公開係数・内部AI・宣伝上の回収率は推定しない。短期間の的中例、会員数、販売順位を長期能力の証拠にしない。下記は確認できた比較集合で、網羅的レビューの完成ではない。

## ハンディキャップ・専門家

| 対象・確認した出典 | 原理・使う情報・強み | 弱点・得意／不得意条件・ARVEXQ判断 |
|---|---|---|
| [Beyer/DRF](https://promos.drf.com/beyer)、[公式の説明](https://help.drf.com/hc/en-us/articles/25029649780243-All-Access-PPs-includes-both-Beyer-Speed-Figures-and-TimeformUS-Speed-Figures-What-is-the-difference) | 距離・時計・当日の馬場速度を補正して過去に発揮した走行を比較。生時計より条件差を扱える | 同日のvariantの取得時刻が重要。後日訂正指数は漏洩源。個体の状態・戦術を指数だけでは識別できない。内部全係数と独立長期成績未確認。補正時計を研究候補とする |
| [Timeformの能力とハンディキャップ](https://www.timeform.com/horse-racing/features/timeform-ratings/How_Timeform_handicaps_horses) | 過去の着差・斤量・年齢・時間・距離等から能力を査定し、最適条件で発揮可能な能力とコメントを扱う | 能力ratingは勝率ではない。少数走・条件変更で推定不確実性が大きい。日本への換算係数は未検証。能力／今回条件の分離を設計原理として候補にする |
| [Brisnet speed](https://support.brisnet.com/hc/en-us/articles/360056540811-BRIS-SPEED-RATINGS-FAQ)、[pace](https://www.brisnet.com/racing/news/handicappers-library-brisnet-pace-ratings-faq/) | 走破速度とE1/E2/LATEなどの区間を区別。速い終いが早い巡航を意味するとは限らない | 米国データ前提、内部完全式未公開。距離・surface・馬場補正が必要。日本の個体テン1Fを捏造して再現しない |
| [Racing PostのRPR説明](https://help.racingpost.com/hc/en-us/articles/115001699689-Abbreviations-on-the-racecard) | ハンディキャッパーのform ratingを当日斤量に調整 | 詳細係数・独立成績未確認。公開スコアをそのまま日本の勝率に変換する根拠なし |
| [亀谷敬正・血統ビーム本人公式](https://k-beam.com/) | 血統・適性を重視する公開活動を確認。初条件で過去走が少ない際の事前情報という応用仮説 | 完全な事前予想・資金配分・長期成績の独立監査未実施。血統係数、遺伝的因果効果、的中率は未確認。階層的事前情報として保留 |
| [水上学・公開コラム](https://www.keibalab.jp/special/article.html?article=blood.html&gid=20&year=2019) | 血統プロファイルによる条件評価の公開例を確認 | 一記事から継続的優位を推定できない。独立寄与・出走選択の交絡を分離できず保留 |
| 新聞・ラップ・馬場・調教・パドック・騎手厩舎専門家という分類 | 候補情報は適性・状態・展開等に分解できる | 全予想家の発走前全予想と長期購入履歴を取得していない。誰が最良かは結論不能。主観コメントは発表時計・評価者間一致・独立追加効果が必要 |

海外ratingの補正思想は、一定距離を速く走った過去の実績の比較に役立つ。しかし、今回の対戦相手、条件、戦術、状態に依存する確率を同一視できない。これは設計上の推論であり、ARVEXQで各ratingの有効性を測った結果ではない。

## 学術研究・公開AI

| 名称・著者・年・一次資料 | 方法／確認した結果 | 限界と応用 |
|---|---|---|
| Assigning Probabilities to the Outcomes of Multi-Entry Competitions、David A. Harville、1973 [出版社](https://www.tandfonline.com/doi/abs/10.1080/01621459.1973.10482425) | 勝率から全順位へ進む確率モデルの仮定を提示。要旨を確認 | 本文全体のアクセス・今回の日本データ適合は未確認。勝率だけで2/3着を正しく復元できる普遍則ではない |
| Searching for Positive Returns at the Track: A Multinomial Logit Model for Handicapping Horse Races、Ruth N. Bolton / Randall G. Chapman、1986 [出版社](https://pubsonline.informs.org/doi/10.1287/mnsc.32.8.1040) | レース内の比較をmultinomial logitで扱う。出版社要旨を確認 | 全結果・現市場での再現は未検証。条件付きlogitを簡潔な学習基準候補にする |
| Computer Based Horse Race Handicapping and Wagering Systems: A Report、William Benter、1994 [公開論文](https://gwern.net/doc/statistics/decision/1994-benter.pdf) | 香港データで基本モデルと市場の対数確率を別サンプルで結合し、確率校正と馬券期待値を分離。本文の校正表・市場結合式・順位近似の偏りを確認 | 著者報告であり現在のARVEXQで再現していない。香港の係数は移植しない。予測時点市場と基本予測の独立追加情報を測る考え方を採用候補にする |
| Optimal speed in Thoroughbred horse racing、Quentin Mercier / Amandine Aftalion、2020 [PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0235024) | 速度・推進力・無酸素エネルギーの連立ODEを最適制御。Chantillyの約10レース、10Hz位置速度でパラメータを同定 | 約100レースの測位装置精度検証と予測モデルの検証件数を混同しない。生理パラメータは推定。日本の発走前全馬GPSなしで再現不能。物理メカニズムの候補として利用 |
| Explaining the Favorite-Longshot Bias: Is it Risk-Love or Misperceptions?、Erik Snowberg / Justin Wolfers、2010 [NBER](https://www.nber.org/papers/w15923) | 市場のfavorite-longshot biasの説明を比較し、確率認識の歪みを支持する結果を報告 | 日本全券種で同じ係数とは限らない。人気薄の高配当と高期待値を同一視しない。本文の全データ再分析は未実施 |
| 部分再帰型ニューラルネットワークを用いた最適な競馬のbetting戦略、杉山航太 / 山下遥、2023 [J-STAGE](https://www.jstage.jst.go.jp/article/pjsai/JSAI2023/0/JSAI2023_2L6GS302/_article/-char/ja) | 時系列と属性を扱う部分再帰NN、勝率とオッズ期待値に基づく戦略。要旨と公開PDFへのアクセスを確認 | PDF抽出から数値実績を確実に読めず、精度・回収率の数値は転記しない。オッズ時刻と時系列分割の再監査が必要 |
| 勝馬予測タスクにおけるRankNetの応用：条件別データセットを用いた予測モデルの構築、藤澤敬之 / 伏見卓恭、2024 [J-STAGE](https://www.jstage.jst.go.jp/article/jsaikbs/132/0/132_19/_article/-char/ja) | 条件別データとRankNetを扱う研究の書誌・公開PDFを確認 | 確実に抽出できない数値結果は記録しない。順位学習のscoreは校正済み勝率ではない。ARVEXQ再実験未実施 |
| CatBoost: unbiased boosting with categorical features、Liudmila Prokhorenkovaほか、2018 [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html) | ordered boostingとカテゴリ統計によるprediction shift対策。一般ベンチマークの比較 | 競馬での勝率改善証拠ではない。ARVEXQ既存CatBoost trainerの存在と訓練済み本番モデルの存在を混同しない |
| [JRA-VAN公開データマイニング](https://jra-van.jp/fun/dm/mining.html)、[対戦モデル説明](https://jra-van.jp/fun/dm/game_mining.html) | 過去速度を教師とするタイム型と、対戦の勝敗を教師とする対戦型。公開説明で騎手・調教師等の入力を確認 | 正規化100点は勝率100%ではない。内部モデルの種類・全係数は未確認。全レース長期成績を今回取得していない |

古典logit／順位モデルは整合性と説明性を持ち、近年モデルは多様な属性・履歴を扱える。しかし異なるデータ集合・予測時計・券種の論文成績をランキングしても、ARVEXQの最良モデルは決まらない。

## 全候補の選定

| 候補 | 入力・学習・出力 | 長所／問題／今回の状態 |
|---|---|---|
| 単純能力指数 | 時計等の観測、固定／学習補正、score | 基準として明確。ただし能力と今回確率は別。現行45/35/20は経験配分で最適性未証明 |
| 条件付きLogistic Regression | レース内特徴、勝者対数尤度、勝率 | 簡潔な第一学習候補。対戦依存と和1を扱える。raw特徴の時計証明が不足して未学習 |
| 階層Bayes／状態空間 | 馬・騎手・厩舎・会場の効果、時系列状態、事後分布 | 少数例の縮約、能力変動を表現。識別性と推論コストを要検証。未学習 |
| Random Forest | 非線形木のbagging、勝者ラベル、確率 | 相互作用を探索可能。レース内整合・校正は別途必要。未実験 |
| XGBoost／LightGBM／CatBoost | 特徴とレース内目的、boosting、score／確率 | 表形式データ候補。カテゴリ時系列統計漏洩に注意。選定済み最良とはしない |
| Learning to Rank／RankNet | レース内の対比較・listwise目的、順位score | 順位最適化に適合。勝率／券種確率の校正が別課題。未実験 |
| NN／Transformer | 履歴列＋属性、教師付き学習、潜在状態／score | 順序と欠損maskを扱える。7日規模では複雑性正当化不能。保留 |
| Graph Neural Network | 出走馬・対戦・コースのgraph、相互作用学習 | レース内干渉を表す候補。データ・計算・説明の負担。保留 |
| Plackett–Luce／Harville | 正のstrength、レース内逐次選択、全順位joint | 数学的整合の簡潔な基準。IIA、展開相互作用、順位ごとの異質性に限界。exact bookkeeping試作をテスト済み、実測採用未承認 |
| 展開Monte Carlo | 学習した開始位置・速度・状態・相互作用の分布 | 異なるシナリオを表現。観測のない生理係数を作ると精密な架空モデルになる。未実装 |
| アンサンブル／市場結合 | 時系列OOF予測、学習した結合、順位joint | 独立情報だけを使えば候補。任意配点は不可。予測時刻オッズ欠損で未実験 |

今回実験したのは保存確率の低次元補正だけで、不採用。全AI方式を実装・比較したとは報告しない。
