"""Parse factual runner fields from observed NAR official card HTML."""
import re

from bs4 import BeautifulSoup
from arvexq.ingest.nar_fields.body_weight import extract as observed_body_weight
from arvexq.ingest.nar_fields.carried_weight import extract as observed_carried_weight


def _official_banei_rows(soup, detail, clean):
    """Read weight facts from the EXISTING multi-row NAR official card layout.

    Its runner is identified by the named .horseNum / .horseName cells.
    Previous-race weight cells and odds must never become today's values.
    """
    known = {clean(str(h.get("name"))): h.get("horseNumber")
             for h in detail.get("horses", []) or [] if h.get("name")}
    results = {}
    for first in soup.select("tr.tBorder"):
        number_cell = first.select_one("td.horseNum")
        name_cell = first.select_one("a.horseName")
        if number_cell is None or name_cell is None:
            continue
        name = clean(name_cell.get_text(" ", strip=True))
        try:
            number = int(number_cell.get_text(" ", strip=True))
        except (TypeError, ValueError):
            continue
        if known.get(name) != number:
            continue
        # Five consecutive outer-table rows comprise this race's horse.
        following = []
        for sibling in first.find_next_siblings("tr"):
            if "tBorder" in (sibling.get("class") or []):
                break
            following.append(sibling)
            if len(following) >= 4:
                break
        load = body = change = None
        for row in following:
            cells = row.find_all("td", recursive=False)
            # Current load is uniquely the fourth cell in the row beginning
            # with sex, coat and birth date, followed by career record.
            if len(cells) >= 4 and cells[0].find("span", class_="male"):
                candidate = clean(cells[3].get_text(" ", strip=True))
                m = re.fullmatch(r"(\d{3})\s+\d+-\d+-\d+-\d+", candidate)
                if m:
                    load = observed_carried_weight([m.group(1)], 0, banei=True)
            for cell in cells:
                if "odds_weight" not in (cell.get("class") or []):
                    continue
                candidate = clean(cell.get_text(" ", strip=True))
                m = re.fullmatch(r"(\d{3,4})\s*(?:kg)?\s*\\(([+-]?\d+)\\)", candidate)
                if m:
                    body, change = observed_body_weight(
                        [m.group(1) + " (" + m.group(2) + ")"], "", 0, -1, banei=True,
                    )
        if body is not None or load is not None:
            results[number] = {"horseNumber": number, "bodyWeight": body,
                               "bodyWeightChange": change, "carriedWeight": load,
                               "source": "NAR公式出馬表"}
    return [results[n] for n in sorted(results)]


def parse_card_html(detail: dict, html: str, clean) -> list[dict]:
    """Return per-horse observed weight/weight-change/carried-weight fields."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    is_banei = (detail.get("track") == "帯広ば" or detail.get("analysisMode") == "ばんえい")
    if is_banei and soup.select("tr.tBorder td.horseNum"):
        return _official_banei_rows(soup, detail, clean)
    known = {
        clean(h.get("name")): int(h.get("horseNumber") or 0)
        for h in detail.get("horses", []) or []
        if h.get("name") and int(h.get("horseNumber") or 0) > 0
    }
    out_by_no = {}

    def horse_no_from_row(vals, rowtxt):
        for name, hno in known.items():
            if name and name in rowtxt:
                return hno
        nums = []
        for value in vals[:8]:
            match = re.fullmatch(r"\D*(\d{1,2})\D*", value)
            if match:
                number = int(match.group(1))
                if 1 <= number <= 18:
                    nums.append(number)
        return nums[-1] if nums else 0

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_vals = []
        header_idx = -1
        for row_index, row in enumerate(rows[:8]):
            values = [clean(cell.get_text(" ", strip=True))
                      for cell in row.find_all(["th", "td"], recursive=False)]
            compact = [re.sub(r"\s+", "", value) for value in values]
            if any("馬体重" in value for value in compact):
                header_vals = compact
                header_idx = row_index
                break

        body_weight_idx = change_idx = carried_weight_idx = -1
        if header_vals:
            for index, value in enumerate(header_vals):
                if body_weight_idx < 0 and "馬体重" in value:
                    body_weight_idx = index
                if change_idx < 0 and ("変更" in value or "増減" in value):
                    change_idx = index
                if carried_weight_idx < 0 and ("負担重量" in value or "斤量" in value or value == "重量"):
                    carried_weight_idx = index

        for row in rows[header_idx + 1 if header_idx >= 0 else 0:]:
            cells = row.find_all(["th", "td"], recursive=False)
            values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
            row_text = clean(row.get_text(" ", strip=True))
            if not values or not row_text:
                continue
            horse_number = horse_no_from_row(values, row_text)
            if not horse_number:
                continue

            is_banei = (detail.get("track") == "帯広ば" or detail.get("analysisMode") == "ばんえい")
            weight, change = observed_body_weight(
                values, row_text, body_weight_idx, change_idx, banei=is_banei,
            )
            carried = observed_carried_weight(
                values, carried_weight_idx, banei=is_banei,
            )

            if not weight and carried is None:
                continue
            out_by_no[horse_number] = {
                "horseNumber": horse_number,
                "bodyWeight": weight,
                "bodyWeightChange": change,
                "carriedWeight": carried,
                "source": "NAR公式出馬表",
            }

    return [out_by_no[number] for number in sorted(out_by_no)]
