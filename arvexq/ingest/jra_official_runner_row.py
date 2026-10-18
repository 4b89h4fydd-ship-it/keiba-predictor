"""Identify the official JRA runner number among row-leading cells."""
import re

def extract(cells, text_of):
    for index, cell in enumerate(cells[:3]):
        match = re.fullmatch(r"\s*(\d{1,2})\s*", text_of(cell))
        if match:
            number = int(match.group(1))
            if 1 <= number <= 18:
                return number, index
    return 0, -1
