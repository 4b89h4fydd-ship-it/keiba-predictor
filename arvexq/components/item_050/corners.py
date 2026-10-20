"""50: Ordered actual corner positions from individual list items."""
import re

def extract_corners(cell):
    positions=[]
    for li in cell.find_all("li"):
        text=li.get_text(" ",strip=True)
        if re.fullmatch(r"\d{1,2}",text):positions.append(int(text))
    return positions
