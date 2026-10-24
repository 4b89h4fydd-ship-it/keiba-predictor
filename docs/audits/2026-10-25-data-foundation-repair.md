# ARVEXQ データ基盤 実測監査・修復（2026-10-25 JST）

**状態：未完了。main統合・本番デプロイ・D1書込み・MotherDuck書込みは実施していない。**

基準commit: `d6b7c04b491fbbe15906a818d6f00670a09ff757`。Open PR 47件を照合し、#474（新馬・障害）、#472/#469（新方式）、#368/#369/#405（データ・表示）の変更は取り込まず保持。

## 実データ読取

| 日付 | D1対象一覧 | 詳細復元 | 延べ出走馬 | 過去走あり | 結果あり | 対象外の帯広 |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10-22 | 48 | 48 | 505 | 468 | 48 | 0 |
| 2026-10-23 | 36 | 36 | 380 | 371 | 35 | 0 |
| 2026-10-24 | 60 | 60 | 729 | 635 | 60 | 12 |
| 2026-10-25 | 78 | 78 | 897 | 825 | 0 | 12 |

母数はD1の対象一覧との照合であり、独立した公式全開催表との100%網羅証明ではない。馬数は取消等を含む保存名簿の行数で、fieldSizeとの差分は自動修正していない。新馬の過去走0件は通常の状態であり、過去走有無を欠測不具合と同一視しない。

MotherDuck `my_db.arvexq_analytics.race_snapshots` は401件（10/15〜21）、4,309頭。全行はfull-payload圧縮形式。10/22以降0件をSQLで確認。現行リポジトリにMotherDuckへの定期同期コード・workflowは見つからず、停止ジョブがあるとは断定できない。

発走前証拠 `morningTicketEvidence` はMotherDuckの保持対象索引で0件。fusionInputsは圧縮索引だけでは原本全体の不在を断定できない（401圧縮原本すべての復元照合は未了）。今回D1から復元した222件ではfusionInputs・morningTicketEvidenceとも0件。取得時刻が発走前であるだけでは独立した発走前保存・評価証明にならない。

## 原因と修復

- 血統の父または母が一つあるだけで追加検索を止める条件を、父・母・母父の項目別判定へ修正。
- 部分血統dictを丸ごと残すため欠けた母系が補完されない問題を修復。既存の祖先値は保持し、補助取得元との矛盾を `_pedigreeEvidence` に保存。日時は取得日時であり発走前公表証明とはしない。
- app.pyの既存SmartRc/netkeiba/extraの血統マージで既存値が無条件上書きされる問題を同じ関数へ統一。
- 短い過去走マージで日付不明・書式違いの行が境界を通る問題を日付正規化と不明日付拒否で修復。
- circuit不明をNARとみなす補完経路を停止し、既存値を保持して未判定を明示。
- 全保存経路にかかる `_strip_excluded` がtraining/workouts/調教を削除していた。指示に基づき観測値とコメントの保持を許可。trainingScoreなどの旧スコアは復活させず、予想計算は変更しない。
- D1読取スクリプトに既存prefetch/APIと同じ帯広除外を適用。対象外IDはレポートに残し、D1の原本は削除しない。
- 補完処理に取得元×domainの試行・空応答・成功・失敗・リトライ・時間・取得日時、血統/過去走/関係者の補完前後件数を追加。応答が非空であることは有用な証拠の取得とは別。

## 改善前後と不足

実データ222件では父・母・母父の完全血統、調教の検査対象項目、動画由来earlyTiming、jumpStats/obstacleStatsは未取得。新馬・障害専用specialRaceBoxも現本番にはない。これらの欠測率の実測改善はまだ0ポイント。修復後の登録済みモック取得元では血統完全率0/1→1/1を確認したが、実レース取得実績には計上しない。

10/24障害1レース10頭・10/25障害1レース11頭は既存過去走を復元できた。飛越・障害専用の実測値や学習入力の充足を意味しない。

10/22〜25の222件は既存MotherDuckスキーマ向けに入力ファイルを準備（同じfull-payload形式）。既存401件をUPDATE/DELETEしない追記案。MotherDuck書込ツールの明示確認が必要なため未実行。発走前原本の後付け作成ではない。

## 取得元40件の接続テスト

HTTP成功は公開入口の閲覧テストのみ。自動取得・商用利用の許諾や全項目の成功率とは異なる。収録期間・料金・公開時刻・欠測率が未確認のものは未確認のまま記録。既存の正規取得元を廃止せず、未許諾の大量取得は有効化しない。

| 取得元 | 中央/地方 | データ候補 | HTTP入口 | 条件・不足 |
|---|---|---|---|---|
| [JRA公式レース結果](https://www.jra.go.jp/keiba/) | JRA | result,corner,race_lap,horse | 200 | 公式閲覧。再配信・大量取得の条件は要確認 |
| [JRA-VAN DataLab.](https://jra-van.jp/dlb/) | JRA | history,odds,result,sectional | 200 | 一般DataLab契約ではスマホ商用再配信不可。JRADB商用契約が必要 |
| [地方競馬情報サイト/NAR](https://www.keiba.go.jp/) | NAR | entries,result,corner,race_lap,history | 200 | 公式情報。利用規約に無断転載禁止 |
| [NAR公式CSV](https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf) | NAR | entries,odds,payout,race_lap,corner | 200 | 2026 CSV。ZIPダウンロードはページから。商用許諾要確認 |
| [南関東4競馬場公式](https://www.nankankeiba.com/race_detail_search/search.do) | NAR | entries,history,corner,result | 200 | 浦和/船橋/大井/川崎 |
| [競馬ブック](https://p.keibabook.co.jp/) | both | history,corner,horse_early3f,trip | 200 | 南関東/道営の前半3F/不利マークは有料・利用許諾要 |
| [netkeibaデータベース](https://db.sp.netkeiba.com/) | both | history,corner,result,horse,connections | 200 | 一部有料。利用許諾要 |
| [netkeiba個別ラップ/AI展開](https://race.netkeiba.com/AI/AI.html) | both | horse_sectional,estimated_sectional,pace_forecast | 200 | 計測ラップと予測ラップを区別 |
| [楽天競馬](https://keiba.rakuten.co.jp/) | NAR | entries,result,odds,video | 200 | 地方全場。第三者配信用契約未確認 |
| [オッズパーク](https://www.oddspark.com/keiba/SearchRace.do) | NAR | history,entries,result,corner | 200 | 地方レースDB。第三者配信用契約未確認 |
| [JBIS-Search](https://www.jbis.or.jp/) | both | pedigree,horse,history,result | HTTPError: HTTP Error 403: Forbidden | 中央/地方/障害の検索 |
| [JRDB](https://jrdb.com/data_introduction/) | JRA | pace,ratings,trip,horse,trainer,jockey | 200 | 有償データ仕様/外部利用契約要 |
| [競馬ラボ](https://www.keibalab.jp/) | JRA | entries,result,corner,last3f | HTTPError: HTTP Error 503: Service Unavailable | 競馬ラボレースDB |
| [ウマニティ](https://umanity.jp/racedata/database_search_race.php) | JRA | history,result,forecast | 200 | 中央競馬検索 |
| [SPAIA競馬](https://spaia-keiba.com/ai/ai-predictions) | JRA | forecast,pace,statistics | 202 | 予想比較・検証用。無許可でモデル予想を転載しない |
| [スポニチ競馬Web](https://keiba.sponichi.co.jp/race_result/20260905) | JRA | result,pace_comment,forecast | 200 | H/M/Sペースの短評を掲載 |
| [サンスポ レースNAVI](https://racenavi.sanspo.com/) | NAR | entries,result,schedule | 200 | 地方競馬を含むレース一覧 |
| [KEIBA Intelligence](https://keiba-intelligence.jp/) | both | history,forecast,result | 200 | 中央/南関東のAI分析アーカイブ |
| [SPAT4](https://www.nankankeiba.com/) | NAR | entries,odds,video | 200 | 公式誘導先。専用データ配信利用は未確認 |
| [NAR競馬ライブ情報](https://www.keiba.go.jp/live/) | NAR | video,trip_review | 200 | 映像確認。構造化自動取得ではない |
| [ばんえい十勝公式 成績表](https://www.banei-keiba.or.jp/race_starting_pdf.php) | NAR | entries,result,schedule | HTTPError: HTTP Error 500: Internal Server Error | 帯広ばんえい。平地のコーナー順位とは別形式 |
| [ホッカイドウ競馬公式](https://www.hokkaidokeiba.net/raceinfo/) | NAR | history,result,odds,entries,video | 200 | 門別。前5走出走表・成績表 |
| [岩手競馬公式](https://www.iwatekeiba.or.jp/) | NAR | schedule,result,trainer,jockey,statistics | 200 | 盛岡・水沢。能力検査・騎手リーディング等 |
| [金沢競馬公式](https://www.kanazawakeiba.com/race/) | NAR | entries,result,odds,video | 200 | 結果・オッズはNARへのリンクも含む |
| [笠松けいば公式](https://www.kasamatsu-keiba.com/) | NAR | schedule,result,entries | 200 | 東海公営競馬情報・開催成績 |
| [名古屋けいば公式成績表](https://www.nagoyakeiba.com/info/race/racereport/) | NAR | result,entries,schedule | 200 | 名古屋の公式競走成績表を公開 |
| [園田・姫路競馬公式](https://www.sonoda-himeji.jp/schedule) | NAR | schedule,result,video | 200 | 公式開催日程。出馬表と成績はNAR参照 |
| [高知けいば公式](https://ns.keiba.or.jp/) | NAR | result,trip,video | 200 | 発走調教不十分など競走関連発表と成績 |
| [佐賀競馬公式](https://www.sagakeiba.net/graderaceschedule/) | NAR | schedule,result,video | HTTPError: HTTP Error 503: Service Unavailable | 開催・騎乗・除外変更の公式案内 |
| [netkeiba競馬新聞データ解説](https://race.sp.netkeiba.com/race/newspaper_master.html) | JRA | horse_early3f,corner,horse_sectional,pace_forecast | 200 | 前半3F/追走指数など。商品内容と利用条件を要確認 |
| [競馬エイト電子版](https://eight.race.sanspo.com/) | JRA | horse,history,forecast | 200 | 全JRAレースの新聞形式。契約下の閲覧サービスで自動配信・転載権限は別 |
| [スマート出馬表](https://www.smartrc.jp/v4/) | both | entries,pedigree,history | 200 | 閲覧・契約と機械取得権限は別。既存SMARTRC_FEED_URLのみ利用 |
| [スポーツナビ競馬](https://sports.yahoo.co.jp/keiba/) | JRA | entries,result,odds,horse | 200 | 公開閲覧。自動取得・商用利用権限は未確認 |
| [dメニュースポーツ競馬](https://sports.smt.docomo.ne.jp/keiba/data/) | JRA | horse,history,result | 200 | JRA提供データの閲覧。二次利用権限は別途確認 |
| [JRA競馬場](https://www.jra.go.jp/facilities/race/) | JRA | course,obstacle | HTTPError: HTTP Error 403: Forbidden | 公式コース資料。初角距離は距離・内外回り・発走位置別の原典必須 |
| [JRA調教情報](https://www.jra.go.jp/keiba/) | JRA | training,debut,horse | 200 | 公開対象・掲載時刻をレース別確認。全新馬の全調教を網羅するとは限らない |
| [NAR裁決・パトロール](https://www.keiba.go.jp/qa.html) | NAR | trip,video | 200 | 裁決翌日まで、DG全周映像1週以内。商用利用と保存は別途許諾必要 |
| [気象庁観測CSV・XML](https://www.data.jma.go.jp/developer/index.html) | both | weather,precipitation,wind,temperature | 200 | 公共データ利用規約。出典・加工表記。観測地点と競馬場の違いを保持 |
| [国土地理院地図](https://maps.gsi.go.jp/) | both | geometry,elevation | 200 | 一般地形と実際の走路距離を混同しない。個別レイヤー利用条件確認 |
| [地方競馬ウォッチ・関連研究候補](https://yukochi.com/) | NAR | forecast,statistics | 200 | ユーザー指定の調査対象。実測値・予想・転載許諾を区別。自動取得未承認 |

40入口中34件HTTP 200、SPAIAは202、JBIS/JRAコース403、競馬ラボ/佐賀503、帯広500。単発テスト結果であり恒久的な利用可否は断定しない。Firecrawlは残高不足で実行不可、Web検索と公開資料で条件を照合。

気象庁の明示公開CSVから1時間降水量1,284観測地点を実取得（cp932、品質記号・観測時刻を保持）。競馬場と観測地点の照合が未検証のためレースの馬場状態へ置換しない。

権利確認の一次資料： [NAR FAQ](https://www.keiba.go.jp/qa.html)、[NAR規約](https://www.keiba.go.jp/terms.html)、[JBIS業務利用](https://www.jbis.or.jp/help/use/)、[JRDB規約](https://jrdb.com/terms)、[JRA-VAN規約](https://jravan.jp/info/rule.html)、[気象庁条件](https://www.jma.go.jp/jma/kishou/info/coment.html)、[気象庁CSV仕様](https://www.data.jma.go.jp/stats/data/mdrr/docs/csv_dl_readme.html)。NAR・JBIS・JRDBは通常公開/個人利用を商用権限とみなさない。契約データ・予想販売への利用許諾・映像解析権限の証拠は未提供。

## 本番アプリで観測した状態

本番 `https://kraizweb1.4b89h4fydd.workers.dev`（BUILD v330）をブラウザで確認。10/25京都5R「2歳新馬」は8頭の馬名・騎手・保存オッズを表示。印は未生成、検証済み買い目は未取得。ノイエルングをタップすると詳細画面は開くが「新方式の予想は未保存です。過去走の事実のみ表示します。」のみ。新馬に必要な血統・調教の表示改善は未完了。iPhone実機検証ではない。

## 検証・残作業

修正時の全Python回帰1092 passed・64 subtests passed、PWA build v330成功。追加最終差分のテスト/CI結果はPRに記録。ローカル成功と本番成功は区別する。

- 40取得元の全データ項目の権限・料金・収録期間・更新時刻確認は未完了。HTTP入口テストだけで網羅済みとしない。
- 生データの保存と読取復元は確認。既存D1書込み/readbackの新規一致検査、MotherDuck追記、継続同期運用は未実施。
- 新しい血統/調教/新馬/飛越/映像/独立予想家・AI/3連系オッズの発走前データ取得と予想入力への実測接続は未完了。予想方式・印・買い目・UIは変更しない。
- 新取得元統合後の実レース欠測率の改善、時刻漏洩ゼロ、結果照合と的中率/回収率の改善証明は未完了。
- main統合と本番デプロイにはユーザーの明示承認が必要。研究PRはマージしない。

## SmartRc既存契約フィードの血統接続（追記）

既存の `_smart_normalize_row` は血統を出力せず、`_start_enrichment.get_smart` は無条件に空配列を返していた。父・母・母父の観測値を保持し、既存 `SMARTRC_FEED_URL` が設定された場合だけ同じ `_fetch_smartrc` を利用する血統専用adapterを既存registryと補完処理へ接続した。公開ページの新規スクレイピングは作成せず、SmartRcのtempo・ratings・予想スコアは再開しない。馬番と馬名が矛盾する場合や複数候補は拒否する。app.pyの既存3取得元のマージも矛盾する馬番・馬名を拒否する。

実契約フィードURL・利用許諾・認証情報はこの実行環境にないため、実SmartRcからの血統取得は未実施。中央・地方の同じ既存補完経路、正規化、部分欠損補完、既存値不変、別馬拒否はテスト用応答で検証した。実レース欠測率の改善には計上しない。

## 最終実測追記

SmartRc/本人照合修復を含む全Python回帰1096 passed・64 subtests passed、PWA build v330成功。10/25の公式掲載予定はJRAの東京・京都・新潟各12=36レース、NARの盛岡12・金沢9・高知11・佐賀10=42レースで、D1対象詳細78件と件数一致。JRA番組は予定であり変更・中止に対する最終出馬表と全馬の照合ではない。出典: https://www.jra.go.jp/keiba/calendar2026/2026/10/1025.html 、https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop 。ローカルJRA直取得はタイムアウト、ローカルNAR summaryは未投入SQLiteの0件なので、これらを公式開催0件や正常取得とは判定しない。Web取得した公式掲載で件数を補助照合した。

MotherDuck既存401件のsha256は、保存JSON文字列そのもののSHAと401/401一致。追記候補222件も同じraw-JSON SHA契約に合わせ、保存オブジェクトをcanonical順に整列してから出力。既存の圧縮形式を維持し、後付け予想原本は作らない。
