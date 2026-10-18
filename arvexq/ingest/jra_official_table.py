"""Locate the observed JRA official race-card runners table.

Only identify the DOM section; individual factual fields stay with dedicated parsers.
"""
import re

def select_runners_table(soup):
    for table in soup.find_all("table"):
        heading=table.find("thead") or table
        text=re.sub(r"\s+"," ",heading.get_text(" ",strip=True)).strip()
        if "馬番" in text and "前走" in text:
            return table
    return None
