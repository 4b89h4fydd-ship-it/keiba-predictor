"""Parse factual runner fields from observed NAR official card HTML."""
import re

from bs4 import BeautifulSoup


def parse_card_html(detail: dict, html: str, clean) -> list[dict]:
    """Return per-horse observed weight/weight-change/carried-weight fields."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
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

    def parse_weight_cell(value):
        match = re.search(
            r"(?<!\d)(\d{3})(?:\s*(?:kg)?)?(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?(?!\d)",
            value, re.I,
        )
        if not match:
            return None, None
        weight = int(match.group(1))
        if not 250 <= weight <= 800:
            return None, None
        change = int(match.group(2)) if match.group(2) is not None else None
        return weight, change

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

            weight = change = carried = None
            if 0 <= carried_weight_idx < len(values):
                match = re.search(r"(?<!\d)(\d{2}(?:\.\d)?)(?!\d)", values[carried_weight_idx])
                if match:
                    try:
                        observed = float(match.group(1))
                        if 35 <= observed <= 80:
                            carried = round(observed, 1)
                    except Exception:
                        pass

            if 0 <= body_weight_idx < len(values):
                weight, change = parse_weight_cell(values[body_weight_idx])
                if weight and change is None and 0 <= change_idx < len(values):
                    match = re.search(r"([+\-]?\d{1,3})", values[change_idx])
                    if match:
                        observed = int(match.group(1))
                        if -99 <= observed <= 99:
                            change = observed

            if not weight:
                match = re.search(r"(?<!\d)(\d{3})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]", row_text, re.I)
                if match:
                    observed = int(match.group(1))
                    if 250 <= observed <= 800:
                        weight, change = observed, int(match.group(2))

            if not weight:
                for index, value in enumerate(values[:24]):
                    if not re.fullmatch(r"\d{3}", value):
                        continue
                    observed = int(value)
                    if not 250 <= observed <= 800:
                        continue
                    weight = observed
                    if index + 1 < len(values):
                        match = re.fullmatch(r"\s*([+\-]?\d{1,2})\s*", values[index + 1])
                        if match:
                            change = int(match.group(1))
                    break

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
