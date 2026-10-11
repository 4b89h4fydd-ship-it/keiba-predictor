"""environment/parsers: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.scalars import _clean
from arvexq.normalize.scalars import _scratch_status
from bs4 import BeautifulSoup
import re


def _env_clean_weather(v: str) -> str:
    s=_clean(v)
    for x in ("小雨","小雪","晴","曇","雨","雪"):
        if x in s:return x
    return "不明"


def _env_clean_condition(v: str) -> str:
    s=_clean(v)
    for x in ("不良","稍重","重","良"):
        if x in s:return x
    return "不明"


def _parse_nar_environment_html(html: str, *, _env_clean_condition, _env_clean_weather) -> dict:
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


def _parse_jra_environment_html(html: str, surface: str='', *, _env_clean_condition, _env_clean_weather, _jra_text) -> dict:
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    full=_jra_text(soup)
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
