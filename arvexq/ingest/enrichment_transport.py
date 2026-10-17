"""External enrichment feed URL formation and authenticated JSON fetch."""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

def _format_feed_url(base:str,detail:dict)->str:
    vals={"date":str(detail.get("date") or ""),"yyyymmdd":str(detail.get("date") or "").replace("-",""),"track":str(detail.get("track") or ""),"race":str(detail.get("raceNumber") or ""),"circuit":str(detail.get("circuit") or ""),"race_id":str(detail.get("id") or "")}
    out=base; used=False
    for k,v in vals.items():
        token="{"+k+"}"
        if token in out:out=out.replace(token,urllib.parse.quote(v));used=True
    if not used:out+=("&" if "?" in out else "?")+urllib.parse.urlencode({"date":vals["date"],"track":vals["track"],"race":vals["race"],"circuit":vals["circuit"]})
    return out

def _fetch_json_url(url:str,timeout:float=4.0,token:str=""):
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/7.7)","Accept":"application/json,text/plain,*/*","Accept-Language":"ja-JP,ja;q=0.9"}
    if token:headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as res:return json.loads(res.read().decode("utf-8","ignore"))

