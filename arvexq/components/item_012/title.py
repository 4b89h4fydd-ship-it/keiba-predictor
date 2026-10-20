"""#12 Explicit official race title from heading nodes, without model scores."""
import re
def extract(soup,race_no,blocked):
    for node in soup.find_all(["h2","h3"]):
        text=re.sub(r"\s+"," ",node.get_text(" ",strip=True)).strip()
        if not text or len(text)>=80 or blocked.search(text) or "出馬表" in text:continue
        if re.match(r"^\d+レース$",text):continue
        return text
    return f"{race_no}R"
