"""NAR horse scratches and exclusions, independent of weather/going."""
import re
from arvexq.ingest.field_normalization import _clean, _scratch_status

def parse_nar_scratches(soup) -> dict[int, str]:
    scratches = {}
    for row in soup.find_all("tr"):
        status = _scratch_status(_clean(row.get_text(" ", strip=True)))
        if not status:
            continue
        numbers = []
        for cell in row.find_all(["th", "td"])[:4]:
            match = re.fullmatch(r"\D*(\d{1,2})\D*", _clean(cell.get_text(" ", strip=True)))
            if match:
                number = int(match.group(1))
                if 1 <= number <= 18:
                    numbers.append(number)
        if numbers:
            horse_number = numbers[1] if len(numbers) >= 2 else numbers[0]
            scratches[horse_number] = status
    return scratches
