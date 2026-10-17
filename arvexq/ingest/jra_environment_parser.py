"""Independent JRA weather and surface-going HTML parser."""
import re
from bs4 import BeautifulSoup
from arvexq.ingest.environment_values import _env_clean_weather, _env_clean_condition

def _parse_jra_environment_html(html:str, surface:str="")->dict:
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    full=soup.get_text(' ',strip=True)
    out={"surfaceConditions":{}}
    wm=re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)",full)
    if wm:out["weather"]=_env_clean_weather(wm.group(1))
    for surf,label in (("芝","芝"),("ダート","ダート")):
        cm=re.search(re.escape(label)+r"\s*[：:]?\s*(不良|稍重|重|良)",full)
        if cm:out["surfaceConditions"][surf]=_env_clean_condition(cm.group(1))
    if surface=="障害":
        c=out["surfaceConditions"].get("芝") or out["surfaceConditions"].get("ダート")
    else:
        c=out["surfaceConditions"].get(surface)
    if c:out["condition"]=c
    return out

