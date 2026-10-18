"""Extract a published affiliation from trainer metadata, never race location."""
import re
from .dom import horse_info, text

LABELS = ("美浦", "栗東", "本会外", "地方", "外国", "北海道", "岩手", "浦和",
          "船橋", "大井", "川崎", "金沢", "笠松", "愛知", "名古屋", "兵庫",
          "園田", "姫路", "高知", "佐賀", "ばんえい", "帯広")
PATTERN = re.compile(r"(?:^|[\s(（\[【・･])(" + "|".join(map(re.escape, LABELS))
                     + r")(?=$|[\s)）\]】・･])")


def from_text(value: str | None) -> str:
    match = PATTERN.search(value or "")
    return match.group(1) if match else ""


def extract(row) -> str:
    info = horse_info(row)
    for node in (row.select_one("td.Trainer"),
                 info.select_one("div.Horse05") if info is not None else None):
        value = from_text(text(node))
        if value:
            return value
    return ""
