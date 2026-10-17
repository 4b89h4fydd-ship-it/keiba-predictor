"""Official NAR weather, going and scratch HTML parsing, independent of API."""
import re
from bs4 import BeautifulSoup
from arvexq.ingest.field_normalization import _clean, _scratch_status
from arvexq.ingest.environment_values import _env_clean_weather, _env_clean_condition

def _parse_nar_environment_html(html:str)->dict:
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    full=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
    wm=re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)",full)
    cm=re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)",full)
    out={"scratchMap":{}}
    if wm:out["weather"]=_env_clean_weather(wm.group(1))
    if cm:out["condition"]=_env_clean_condition(cm.group(1))
    for tr in soup.find_all("tr"):
        tx=_clean(tr.get_text(" ",strip=True))
        st=_scratch_status(tx)
        if not st:continue
        nums=[]
        for c in tr.find_all(["th","td"])[:4]:
            m=re.fullmatch(r"\D*(\d{1,2})\D*",_clean(c.get_text(" ",strip=True)))
            if m:
                v=int(m.group(1))
                if 1<=v<=18:nums.append(v)
        if nums:
            no=nums[1] if len(nums)>=2 else nums[0]
            out["scratchMap"][no]=st
    return out

