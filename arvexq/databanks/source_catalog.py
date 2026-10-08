"""Audited source-discovery inventory, not a declaration of extraction rights.

Discovery is deliberately open-ended: new sources can be added via the
authorized feed configuration without being in this inventory.
"""
from __future__ import annotations

from typing import Any

# id / label / circuit / verified public entry point / available data families / caveat
SOURCE_CATALOG: list[list[str]] = [["jra_official","JRA公式レース結果","JRA","https://www.jra.go.jp/keiba/","result,corner,race_lap,horse","公式閲覧。再配信・大量取得の条件は要確認"],
    ["jra_van","JRA-VAN DataLab.","JRA","https://jra-van.jp/dlb/","history,odds,result,sectional","商用ライセンス要確認。JV-LinkはWindows専用"],
    ["nar_official","地方競馬情報サイト/NAR","NAR","https://www.keiba.go.jp/","entries,result,corner,race_lap,history","公式情報。利用規約に無断転載禁止"],
    ["nar_csv","NAR公式CSV","NAR","https://www.keiba.go.jp/pdf/manual/data_pdf_manual.pdf","entries,odds,payout,race_lap,corner","2026 CSV。ZIPダウンロードはページから。商用許諾要確認"],
    ["nankan_official","南関東4競馬場公式","NAR","https://www.nankankeiba.com/race_detail_search/search.do","entries,history,corner,result","浦和/船橋/大井/川崎"],
    ["keibabook","競馬ブック","both","https://p.keibabook.co.jp/","history,corner,horse_early3f,trip","南関東/道営の前半3F/不利マークは有料・利用許諾要"],
    ["netkeiba","netkeibaデータベース","both","https://db.sp.netkeiba.com/","history,corner,result,horse,connections","一部有料。利用許諾要"],
    ["netkeiba_ai","netkeiba個別ラップ/AI展開","both","https://race.netkeiba.com/AI/AI.html","horse_sectional,estimated_sectional,pace_forecast","計測ラップと予測ラップを区別"],
    ["rakuten","楽天競馬","NAR","https://keiba.rakuten.co.jp/","entries,result,odds,video","地方全場。第三者配信用契約未確認"],
    ["oddspark","オッズパーク","NAR","https://www.oddspark.com/keiba/SearchRace.do","history,entries,result,corner","地方レースDB。第三者配信用契約未確認"],
    ["jbis","JBIS-Search","both","https://www.jbis.or.jp/","pedigree,horse,history,result","中央/地方/障害の検索"],
    ["jrdb","JRDB","JRA","https://jrdb.com/data_introduction/","pace,ratings,trip,horse,trainer,jockey","有償データ仕様/外部利用契約要"],
    ["keibalab","競馬ラボ","JRA","https://www.keibalab.jp/","entries,result,corner,last3f","競馬ラボレースDB"],
    ["umanity","ウマニティ","JRA","https://umanity.jp/racedata/database_search_race.php","history,result,forecast","中央競馬検索"],
    ["spaia","SPAIA競馬","JRA","https://spaia-keiba.com/ai/ai-predictions","forecast,pace,statistics","予想比較・検証用。無許可でモデル予想を転載しない"],
    ["sponichi","スポニチ競馬Web","JRA","https://keiba.sponichi.co.jp/race_result/20260905","result,pace_comment,forecast","H/M/Sペースの短評を掲載"],
    ["sanspo","サンスポ レースNAVI","NAR","https://racenavi.sanspo.com/","entries,result,schedule","地方競馬を含むレース一覧"],
    ["keiba_intelligence","KEIBA Intelligence","both","https://keiba-intelligence.jp/","history,forecast,result","中央/南関東のAI分析アーカイブ"],
    ["spat4","SPAT4","NAR","https://www.nankankeiba.com/","entries,odds,video","公式誘導先。専用データ配信利用は未確認"],
    ["nar_live","NAR競馬ライブ情報","NAR","https://www.keiba.go.jp/live/","video,trip_review","映像確認。構造化自動取得ではない"],
    ["banei_official","ばんえい十勝公式 成績表","NAR","https://www.banei-keiba.or.jp/race_starting_pdf.php","entries,result,schedule","帯広ばんえい。平地のコーナー順位とは別形式"],
    ["hokkaido_official","ホッカイドウ競馬公式","NAR","https://www.hokkaidokeiba.net/raceinfo/","history,result,odds,entries,video","門別。前5走出走表・成績表"],
    ["iwate_official","岩手競馬公式","NAR","https://www.iwatekeiba.or.jp/","schedule,result,trainer,jockey,statistics","盛岡・水沢。能力検査・騎手リーディング等"],
    ["kanazawa_official","金沢競馬公式","NAR","https://www.kanazawakeiba.com/race/","entries,result,odds,video","結果・オッズはNARへのリンクも含む"],
    ["kasamatsu_official","笠松けいば公式","NAR","https://www.kasamatsu-keiba.com/","schedule,result,entries","東海公営競馬情報・開催成績"],
    ["nagoya_official","名古屋けいば公式成績表","NAR","https://www.nagoyakeiba.com/info/race/racereport/","result,entries,schedule","名古屋の公式競走成績表を公開"],
    ["hyogo_official","園田・姫路競馬公式","NAR","https://www.sonoda-himeji.jp/schedule","schedule,result,video","公式開催日程。出馬表と成績はNAR参照"],
    ["kochi_official","高知けいば公式","NAR","https://ns.keiba.or.jp/","result,trip,video","発走調教不十分など競走関連発表と成績"],
    ["saga_official","佐賀競馬公式","NAR","https://www.sagakeiba.net/graderaceschedule/","schedule,result,video","開催・騎乗・除外変更の公式案内"],
    ["netkeiba_newspaper","netkeiba競馬新聞データ解説","JRA","https://race.sp.netkeiba.com/race/newspaper_master.html","horse_early3f,corner,horse_sectional,pace_forecast","前半3F/追走指数など。商品内容と利用条件を要確認"]]
NAR_VENUES: list[str] = ["帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"]
VALID_EVIDENCE_FAMILIES = (
    "entries", "horse", "history", "corner", "race_lap", "horse_early3f",
    "horse_sectional", "estimated_sectional", "pace_forecast",
    "jockey", "trainer", "trip", "pedigree", "result", "odds", "payout",
    "video", "statistics", "connections", "ratings", "forecast",
    "pace", "schedule", "trip_review", "last3f", "pace_comment", "sectional",
)


def discovery_inventory() -> list[dict[str, Any]]:
    return [
        {
            "id": key, "label": name, "circuit": circuit,
            "referenceUrl": url, "evidenceFamilies": fields.split(","),
            "usageNote": note, "enabledForExtraction": False,
        }
        for key, name, circuit, url, fields, note in SOURCE_CATALOG
    ]
