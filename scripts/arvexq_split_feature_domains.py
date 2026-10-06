#!/usr/bin/env python3
"""One-shot UI migration for the separated race feature domains."""
from pathlib import Path

path = Path("arvexq/ui/static/app.js")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    text = text.replace(old, new, 1)


replace_once("+tab('詳細','detail')", "", "remove visible detail tab")
replace_once(
    "if(key==='detail')return '<div class=\"accordion-panel\">'+detailPanel(r,p)+'</div>';",
    "",
    "remove standalone detail panel route",
)
replace_once(
    "出走表・全頭診断・詳細・展開予想・買い目から見たい項目を押してください。",
    "出走表・全頭診断・展開予想・買い目から見たい項目を押してください。",
    "update idle navigation copy",
)
replace_once(
    "class=\"diagnosis-horse-main\" data-detail-horse=\"",
    "class=\"diagnosis-horse-main\" data-horse-open=\"",
    "open horse detail from diagnosis",
)
replace_once(
    "馬名をタップすると、その馬の詳細へ移動します。",
    "馬名をタップすると、直近5走・適性・騎手/調教師・血統までまとめて確認できます。",
    "update diagnosis detail hint",
)

required = (
    "function runnerDetailBody",
    "近走データ（直近5走）",
    "data-horse-open",
    "tab('全頭診断','diagnosis')",
    "tab('展開予想','pace')",
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"required marker missing after migration: {marker}")
for marker in ("tab('詳細','detail')", "if(key==='detail')return '<div class=\"accordion-panel\">'+detailPanel"):
    if marker in text:
        raise SystemExit(f"legacy standalone detail UI still reachable: {marker}")

path.write_text(text, encoding="utf-8")
print("ARVEXQ_FEATURE_SPLIT_UI_OK")
