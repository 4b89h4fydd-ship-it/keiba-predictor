# ARVEXQ 新予想ロジック再構築：外部予想手法の統合検討と第1実装修正（2026-10-21）

**状態**: 既存ML研究経路の学習母集団・勝者1位検証の欠陥修正候補。新予想エンジン完成、未来発走前6系統予想、勝率改善の証明、本番採用ではない。

## 保護する仕様
- 旧Stage64正式予想はユーザー明示指示でPR #396により撤去。**復活させない**。
- 現在の公開入口 `arvexq/forecast/engine.py::build_prediction` は意図的に `None`。変更しない。
- 中央と地方を完全分離し、将来の正式出力は能力・脚質・展開・確率・印・おすすめ買い目の6系統。
- 200箱、既存収集→D1→API→UI、既存原票・UI、Stage63/64 `code_hash()` と凍結済み研究を保全。新収集元/商用AI予想コピールート/恣意的な係数は作らない。

## 外部公開手法との突合（自社説明と独立検証を分離）
| 公開主体／方法 | 公開されている着眼点 | 既存コードで確認できる研究材料 | 処理判断 |
|---|---|---|---|
| JRA-VAN走破時計型・対戦型 | 過去の走破速度、馬同士の相対勝敗、騎手/調教師/競走条件 | `mass_feature_factory.py`の同条件時計/速度、レース内relative、`learned_scenarios.py`のpairwise学習候補 | 既存特徴・学習設計を利用。JRA-VAN自体の係数は複製しない |
| SPAIA競馬・複数視点のAI | 近走、コース、ラップ、血統、展開などを独立観点で評価 | `mass_model_training.py`のability/win/podium、研究候補の展開感度 | 同じ結果に学習した複数頭を独立な「票」とは見なさない |
| 競馬ブックのTM/AI指数 | 人の予想、騎手・厩舎・展開・格付け | 既存カテゴリ・条件別特徴 | 他社のランクを根拠なく◎A/B/Cへ変換しない |
| netkeibaコンピューター予想 | 上昇度、脚質、騎手・調教師、血統の条件別評価 | 全履歴、w5、トレンド、脚質/騎手・厩舎特徴 | 実際の上積みは分割された未来区間でアブレーション |
| JRDBの時計・位置取り補正 | 時計、前走不利や位置取り補正 | 既存speed/margin/position/sectional特徴（取得確認済みのみ） | 外部有料指数の値は利用しない |
| ペース崩壊/単騎逃げの仮説 | 先行密度・逃げ争い・後方浮上 | 既存 `learned_scenarios.py` のearly-pressure候補 | シナリオ確率は実測なしに等確率・確定値としない |
| 時系列の独立検証研究 | 着順AUC等だけでなくレース単位で勝馬を当てる目的と分ける | 現行 `train_head` は馬単位logloss/AUC中心 | 第一修正として勝者Top1診断を追加 |

公開資料:
- https://jra-van.jp/fun/dm/mining.html
- https://spaia-keiba.com/ai/ai-predictions
- https://p.keibabook.co.jp/support/faq/detail/12
- https://yoso.sp.netkeiba.com/no1/yosoka_prof.html?yid=266992
- https://jrdb.com/manual
- https://equinedge.com/glossary/racing-data-and-statistics/what-is-a-pace-projection-model-in-horse-racing
- https://doi.org/10.3389/frai.2026.1896192

## 公開予想家の独立視点（調査追補）
| 公開予想家 | 調査可能な方法 | 既存材料・必要な確認 | 判定 |
|---|---|---|---|
| 亀谷敬正氏（血統ビーム） | 血統系統・馬場/条件への適合を中心に検討。公式サイトで血統辞典や条件別記事を継続公開 | 既存 `mass_feature_factory` に父/母父カテゴリ。ただし血統系統の分類や新しい適性重みは入力未検証 | 血統特徴の条件別寄与を比較する研究候補、係数なし |
| 水上学氏（血統トレジャーハンティング） | 血統傾向を絶対評価・相対評価の観点で検討 | 既存血統カテゴリと `relative::` 特徴は存在。氏のノウハウの数値化と勝率実測は未確認 | 既存相対比較の検証観点としてのみ記録 |
| 井内利彰氏（追い切りジャッジ） | 調教時計と当日の坂路・ウッドコース馬場差を一体で評価 | 予想入力に当該レース時点の調教原票が全頭揃うか未検証。前走時計を追い切り時計の代用品にしない | データ契約検証まで未採用 |

一次資料:
- https://k-beam.com/
- https://www.keibalab.jp/yosou/treasure/
- https://jra-van.jp/fun/iuchitraining/
- https://yoso.sp.netkeiba.com/?pid=yosoka_profile&id=43

**競合する予想印の扱い**: 予想家ごとの「◎」は評価基準・券種・対象日が揃わないため、名称だけで多数決にしない。自称回収率や選抜的公開実績を採用の根拠にしない。入手不可の特徴は追加取得経路を自作しない。

## 既存527レースの成績（GitHub race_metrics.csv、3方式×527=1,581行を読み戻し再計算）
- JRA 108母数・87採点: baseline 20/87=22.99%、recent5 16/87=18.39%、shrunk 17/87=19.54%。
- NAR 419母数・332採点: baseline 91/332=27.41%、recent5 97/332=29.22%、shrunk 90/332=27.11%。
- 合計108レースが未採点。いずれも**後追い回顧**。未採点レースを選択的に消して80%到達等と主張しない。
- NAR recent5の回収率126.61%は上位2払戻に約77.76%集中。長期回収率100%達成の証拠ではない。

## 今回実装した第1修正のコード契約
1. `mass_training_dataset.rows_from_frozen_snapshot`: 凍結名簿と確定着順の馬番集合が一致し、重複がなく、勝ち馬1頭が確定したレースだけを学習行化。結果のある馬だけを抜き出して「簡単なレース」に変形することを禁止。欠測レースは無理に補完せず母集団欠測として扱う。
2. `mass_model_training._training_circuit`: JRA/NAR混合学習を明確な例外で禁止し、明示した単一区分だけを受理。既存呼出元 `train_all_heads` は区分別に渡す必要がある。区分別の自動振分や新モデル経路は今回追加していない。
3. `mass_model_training._race_winner_top1`: 日付区切りのtestモデル出力をレース単位の勝者Top1へ集計。曖昧な同点、未確定勝者、馬番重複を採点しない。勝者数・採点母数・除外数を同時に表示。研究ホールドアウトであり、未来発走前凍結済み本番精度の保証ではない。
4. `tests/test_mass_winner_top1_rebuild.py`: 完全名簿、欠損結果、重複馬番、勝者不明、中央地方混入、同点保留を検証。

**禁止した変更**: `forecast.engine`有効化、Stage63/64方式流用、新しい予想ルート/データ経路、3連単/印/おすすめ買い目の恣意的生成、mainマージ、本番D1更新、本番デプロイ。

## 継続前の検証ゲート
- 新コミットについてGitHub Actions/フルpytestの結果を確認。CI通過までコード成功扱いにしない。
- 研究用の1レース1着実測の独立事後テストを、JRA/NAR別に実施。トレーニング日・検証日・テスト日の分離、発走前保存時刻・本人照合・全頭名簿・取消・セクション情報の時点整合を固定する。
- 既存の各特徴ファミリーを1つずつ除外し、レース単位Top1、logloss/Brier、3着内、全コホートカバレッジ、三連単・払戻付きROIを比較。手法の相関を見ずに同一の成績を多数決で数えない。
- 既存6系統への統合は学習済みモデル、校正済み確率、想定展開/印/買い目の契約が独立ホールドアウトを通過した時のみ行う。未来レース保存ができない段階では「完成」としない。

## 第2段階：既存の凍結データで中央・地方別実学習する前の整合修正（2026-10-21）

- 基準: 同じDraft PR #401、main `214cafdf050bb001b486f89c59dfbce1145f9b00`。以前の旧Stage64本番エンジンは撤去したまま。
- GitHubにある `scripts/export_mass_training_dataset.py` は既存 `RaceDataBank` SQLiteの `race_snapshots` → 発走前固定massFeatureSnapshot / final_resultのラベルだけをJSONL化する。新規データ取得経路は追加しない。
- `scripts/train_mass_models.py` は従来5つの研究用ヘッドを呼び出す同じ入口。区分混在の行を無条件に学習させないため、**`--circuit jra` または `--circuit nar` の必須指定**と中身の全行照合を追加。JRA/NARは独立のJSONL・学習保存ディレクトリを使い、重みを共有しない。
- `arvexq/prediction/mass_model_training.py::prepare_head_rows`: ability/win/podium向けの特徴量が1頭でも全欠損なら、該当レースの残りの馬も除外。勝者との順位比較に未登録の馬が残る誤計測を防ぐ。価値/危険の市場条件付きヘッドの既存対象抽出は変更しない。
- 既存 `split_walk_forward` の全日付分離（学習→検証→テスト）、既存40レース最低ゲート、モデルのCatBoost設定、学習原本と保存/表示経路を維持。
- 研究対象になる実データが今回の実行環境に存在することを**確認できていない**。GitHubにある2026-10-21門別12Rの暫定特徴量artifactは `verifiedForTraining=false`、`independentOfficialRoster=false` であり、実学習母集団へ組み込まない。
- 既存の別系統研究 `docs/research/2026-10-18-real-sealed-b-holdout.md` はNAR平地の未使用73Rで1着予測24/73=32.88%、3連単完全一致2/73=2.74%。Bモデルの実績であり、今回のmassモデルの実学習・検証結果ではない。

検証用の既存実行形式（必要なRaceDataBankがある環境のみ）:

```bash
python scripts/export_mass_training_dataset.py /path/to/actual-races.sqlite3 /tmp/jra-frozen.jsonl --circuit 中央
python scripts/train_mass_models.py /tmp/jra-frozen.jsonl /tmp/arvexq-jra-models /tmp/arvexq-jra-runtime --circuit jra

python scripts/export_mass_training_dataset.py /path/to/actual-races.sqlite3 /tmp/nar-frozen.jsonl --circuit 地方
python scripts/train_mass_models.py /tmp/nar-frozen.jsonl /tmp/arvexq-nar-models /tmp/arvexq-nar-runtime --circuit nar
```

`/path/to/actual-races.sqlite3` は利用者が所持する**既存の実データベース**へのプレースホルダーであり、存在確認・実学習実行を意味しない。取り込み元・保存方法を新設したり、欠測データを生成して埋めたりしない。第2段階の本番予想・未来の的中成績は未証明。


## 第3段階：保存済み発走前特徴量の原本ハッシュ検証（2026-10-21）

**実物の原票の照合**:
- GitHub Actions [run 39109130771](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39109130771) artifact ID `12129925831` をダウンロード。ZIP内 `sealed-b-real-holdout.json` の数値を読み戻した。全396R、B方式の適格198R、不適格159R（発走前原本なし）+39R（結果不備）。地方平地の既存B方式は train47 / validation21（1R採点不能）/ test73で、test勝者Top1=24/73。**既存Bモデルの結果であり、新massモデルの成績と混同しない**。
- GitHub Actions [run 39591525811](https://github.com/4b89h4fydd-ship-it/keiba-predictor/actions/runs/39591525811) artifact ID `12342736799` をダウンロード。2026-10-21門別12Rの発走前特徴量は `verifiedForTraining=false`。原本の検査に留め、学習対象に追加しない。モデル評価用に未検証データを無理に埋めない。

**今回の既存学習経路の修正**:
- `mass_training_store.py::frozen_training_rows_from_detail` は、圧縮されていない`massFeatureSnapshot`も、圧縮アーカイブと同じ既存の`_feature_hash`で保存内容を再計算して照合。今までは `featureHash` が単に存在するだけで通過できた。レースID・日付・中央/地方・外側の保存ハッシュ・存在する場合の発走前lockハッシュ・原本アーカイブの明示不整合も照合し、不一致なら学習行を作らない。明示`verifiedForTraining=false`も除外。
- `mass_training_dataset.py::_finish_map` は着順表に同じ馬番が重複した場合、最後の行で上書きする挙動を廃止。不正馬番・着順・曖昧な行の存在時はレースを採点不可とする。既存の全頭一致・1着馬一頭ゲートは維持。
- `tests/test_mass_winner_top1_rebuild.py` に原本ハッシュ改ざん、競馬区分と日付、外側のハッシュ、明示学習不可、重複結果の回帰検証を追加。

**限界**: 正しい内容ハッシュは発走前取得時刻の第三者証明にはならない。新massモデルのJRA/NAR別の真正な発走前学習データの母数・実学習・未来レースの実測成績は依然未確認。現行のStage63/64退役本番予想、既存D1・UI・取得経路・200箱、mainは一切変更していない。



**既存形式との回帰確認**: 新しいcontent-hash検証の初回CI（head `35d1691b`）は既存 `test_mass_feature_transport.py::test_final_training_can_only_read_frozen_preoff_archived_features` が失敗。原因は従来のlossless圧縮データでdetailトップ階層の`circuit`が省略可能なのに、今回のチェックが必須扱いしていたこと。既存の仕様を確認して、detailに`circuit`がある時だけsnapshotと照合するよう修正。欠けているケースは既存SQLiteレース索引`race_snapshots.circuit`とsnapshot側の区分を照合して混入を防ぐ。レースID/日付もSQLite索引とsnapshotが一致しない場合は学習に使わない。テストに従来形式の正常ケース・索引不一致を追加。**最新コミットのCI結果を確認するまでは修正成功と認定しない**。


## 第4段階：既存D1保存形式の読み戻し・実データ確認（2026-10-21 夜）

- **実レースの既存GET API読込**（新経路・書込みなし）：`/api/day?date=YYYY-MM-DD&details=0` と `/api/race/<id>` で10月7日・11日・13日・18日・21日を調査。発見レース数：10/7地方47R、10/11中央24R・地方56R、10/13地方58R、10/18中央36R・地方56R、10/21地方48R。これは全日程の**出走済みレース件数であり、訓練適格件数ではない**。
- 10/21門別12R・園田1R、10/18東京11Rの既存API `arvexqFullPayload`（gzipBase64）を解凍・確認。**全件で `massFeatureSnapshot` / `massFeatureArchive` / `preRacePrediction` は原本にもなし**。確定結果・過去走があっても発走前凍結特徴量を後から創作してはならない。
- 10/11京都1R・東京12R・高知11Rの表示インデックスに `massFeatureArchive` の保存を確認。京都1Rのarchiveは `originHashVerified=true`、`originStatus=verified`（保存ハッシュと内容の整合）。ただし **`preRacePrediction` がない**ため、原本ハッシュだけで発走前固定の時刻・未来独立検証を証明することはできない。保存全体を訓練適格と誤認しない。
- **既存保存読込の欠陥**：`arvexqFullPayload` を持つ圧縮済みレースでは、旧 `mass_training_store.iter_frozen_training_rows` が`massFeatureSnapshot` / `massFeatureArchive` を探す前に表示用の小さなindexから欠損と見なしていた。既存 `arvexq.ingest.full_snapshot_codec.unpack_detail` を読み込み、**内容ハッシュで認証された元原本**を復元後に確定結果・凍結特徴量・SQLiteレースID/日付/区分を判定するよう修正した。新しい取得先・データ経路は作らない。元原本が壊れている場合は不適格のまま。
- 新回帰テストで（1）実際の既存圧縮形式により隠れている凍結特徴量の復元、（2）SQLite内の圧縮原本読戻し、（3）偽造されたハッシュ/壊れたbase64の拒否、（4）表示用結果が本原本と違う時の採用禁止を固定。
- **実データ学習は未実行**：手元のRaceDataBank SQLiteは取得できず、公開D1の保存原本と新massモデルの訓練適格条件を満たす十分な日時付きレース集合を確定できない。日付一覧・数レースの標本監査を全数検査と呼ばない。旧Bモデルの73R中24Rという数字を新massモデルに流用しない。本番予想エンジンは退役のまま。
