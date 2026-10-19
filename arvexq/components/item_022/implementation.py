"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def fetch_central_feed(iso_date: str, history: bool = False) -> list[dict]:
    # Prefer a licensed feed when configured. Otherwise use the official JRA website.
    base = _clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) if history else ""
    if not base:
        base = _clean(os.getenv("CENTRAL_FEED_URL", ""))
    if not base:
        # JRA official fallback is intended for current/near-current racecards.
        return fetch_jra_official(iso_date)
    if "{date}" in base:
        url = base.replace("{date}", iso_date)
    else:
        url = base + ("&" if "?" in base else "?") + "date=" + iso_date
    headers = {"User-Agent": "KeibaPredictor/6.2", "Accept": "application/json"}
    token = _clean(os.getenv("CENTRAL_HISTORY_FEED_TOKEN", "")) if history else ""
    if not token:
        token = _clean(os.getenv("CENTRAL_FEED_TOKEN", ""))
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=float(os.getenv("CENTRAL_FEED_TIMEOUT_SEC", "12"))) as response:
        body = json.loads(response.read().decode("utf-8"))
    rows = body if isinstance(body, list) else body.get("races", [])
    return [r for r in (normalize_central_race(x) for x in rows) if r]

def _netkeiba_get(url:str,timeout:float=4.0,cache_sec:int=45)->str:
    now=time.time()
    with _netkeiba_cache_lock:
        hit=_netkeiba_cache.get(url)
        if hit and now-hit[0]<cache_sec:return hit[1]
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1","Referer":"https://race.netkeiba.com/","Accept-Language":"ja-JP,ja;q=0.9"})
    with urllib.request.urlopen(req,timeout=timeout) as res: txt=_decode_site(res.read())
    with _netkeiba_cache_lock:
        _netkeiba_cache[url]=(now,txt)
        if len(_netkeiba_cache)>80:
            k=min(_netkeiba_cache.items(),key=lambda kv:kv[1][0])[0];_netkeiba_cache.pop(k,None)
    return txt

def _netkeiba_race_summaries(iso_date:str)->list[dict]:
    token=iso_date.replace("-","");url=f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={token}"
    try:html=_netkeiba_get(url,float(os.getenv("NETKEIBA_LIST_TIMEOUT_SEC","3.5")),30 if iso_date==_today_iso() else 86400)
    except Exception as exc:
        print("netkeiba list failed",iso_date,exc);return []
    soup=BeautifulSoup(html,"html.parser");out={}
    for a in soup.find_all("a",href=re.compile(r"race_id=(\d{12})")):
        href=str(a.get("href") or "");m=re.search(r"race_id=(\d{12})",href)
        if not m:continue
        rid=m.group(1);code=rid[4:6];track=NETKEIBA_TRACK_CODES.get(code)
        if not track:continue
        race_no=int(rid[-2:]);node=a
        for _ in range(4):
            if node.parent is None:break
            node=node.parent
            tx=_clean(node.get_text(" ",strip=True))
            if re.search(rf"(?:^|\s){race_no}R(?:\s|$)",tx):break
        tx=_clean(node.get_text(" ",strip=True) if node else a.get_text(" ",strip=True))
        mm=re.search(rf"(?:^|\s){race_no}R\s*(.*?)\s+(\d{{1,2}}:\d{{2}})\s+((?:芝|ダ|障)[^\s]*?)(\d{{3,4}})m(?:\s+(\d+)頭)?",tx)
        title="";start="";surf="";dist=0;field=0
        if mm:
            title=_clean(mm.group(1));start=mm.group(2);kind=mm.group(3);dist=int(mm.group(4));field=int(mm.group(5) or 0);surf="障害" if kind.startswith("障") else ("芝" if kind.startswith("芝") else "ダート")
        else:
            t=re.sub(rf"^.*?{race_no}R\s*","",tx);tm=re.search(r"\b\d{1,2}:\d{2}\b",t)
            if tm:title=_clean(t[:tm.start()]);start=tm.group(0)
            dm=re.search(r"(?:芝|ダ|障)[^0-9]*(\d{3,4})m",t)
            if dm:dist=int(dm.group(1));surf="芝" if "芝" in dm.group(0) else ("障害" if "障" in dm.group(0) else "ダート")
            fm=re.search(r"(\d+)頭",t);field=int(fm.group(1)) if fm else 0
        if not title:title=f"{race_no}R"
        z=normalize_central_race({"id":f"jra-{iso_date}-{track}-{race_no:02d}","date":iso_date,"track":track,"raceNumber":race_no,"title":title,"distance":dist,"surface":surf,"condition":"不明","weather":"不明","fieldSize":field,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"netkeiba一覧","netkeibaRaceId":rid,"_summaryOnly":True})
        if z:out[(track,race_no)]=z
    rows=list(out.values());rows.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    return rows

def _netkeiba_program_race_id(iso_date:str,track:str,race_no:int)->str:
    try:
        p=_jra_program_lookup(iso_date,track,race_no) or {}
        rid=str(p.get("netkeibaRaceId") or "")
        if re.fullmatch(r"\d{12}",rid):return rid
        code=JRA_TRACK_CODE_BY_NAME.get(str(track or ""),"")
        meet=int(p.get("meetingNumber") or 0);day=int(p.get("meetingDay") or 0)
        year=int(str(iso_date)[:4]) if re.match(r"^20\d{2}",str(iso_date)) else 0
        if year and code and meet and day and int(race_no)>0:return f"{year:04d}{code}{meet:02d}{day:02d}{int(race_no):02d}"
    except Exception:pass
    return ""

def _netkeiba_race_id(iso_date:str,track:str,race_no:int)->str:
    rid=_netkeiba_program_race_id(iso_date,track,race_no)
    if rid:return rid
    for r in _netkeiba_race_summaries(iso_date):
        if str(r.get("track"))==str(track) and int(r.get("raceNumber") or 0)==int(race_no):return str(r.get("netkeibaRaceId") or "")
    return ""

def _netkeiba_detail_rows(detail:dict)->list[dict]:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return []
    url=f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}";past=f"https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}&rf=shutuba_submenu"
    html="";past_html=""
    timeout=float(os.getenv("NETKEIBA_DETAIL_TIMEOUT_SEC","3.5"))
    def _get_now():
        try:return _netkeiba_get(url,timeout,20)
        except Exception as exc:print("netkeiba detail failed",rid,exc);return ""
    def _get_past():
        try:return _netkeiba_get(past,timeout,180)
        except Exception as exc:print("netkeiba past failed",rid,exc);return ""
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(_get_now);f2=pool.submit(_get_past);html=f1.result() or "";past_html=f2.result() or ""
    rows={}
    if html:
        soup=BeautifulSoup(html,"html.parser")
        for tr in soup.select("tr.HorseList"):
            horse=_nk_row_horse(tr)
            if not horse:continue
            rows[horse["horseNumber"]]=horse
    if past_html:
        soup=BeautifulSoup(past_html,"html.parser")
        for tr in soup.select("tr.HorseList"):
            horse=_nk_row_horse(tr)
            if not horse:continue
            key=horse["horseNumber"]
            if key not in rows:rows[key]=horse
            rr=[]
            for td in tr.find_all("td"):
                z=_parse_recent_cell(td.get_text(" ",strip=True))
                if z:rr.append(z)
                if len(rr)>=5:break
            if rr:rows[key]["recentRaces"]=rr[:5]
    return list(rows.values())

def _nar_netkeiba_race_id(iso_date:str,track:str,race_no:int)->str:
    code=NAR_NETKEIBA_CODES.get(str(track or '').strip())
    m=re.match(r'^(20\d{2})-(\d{2})-(\d{2})$',str(iso_date or ''))
    if not code or not m or int(race_no)<=0:return ''
    return f"{m.group(1)}{code}{m.group(2)}{m.group(3)}{int(race_no):02d}"

def _nar_netkeiba_preview_rows(detail:dict,force:bool=False)->dict:
    """Fallback before NAR live odds/weights appear: use netkeiba's current NAR card.
    Predicted odds are explicitly tagged and are replaced by official live odds later.
    """
    rid=_nar_netkeiba_race_id(str(detail.get('date') or ''),str(detail.get('track') or ''),int(detail.get('raceNumber') or 0))
    if not rid:return {}
    url=f"https://nar.netkeiba.com/race/shutuba.html?race_id={rid}"
    if force:url+=f"&t={int(time.time()*1000)}"
    try:html=_netkeiba_get(url,float(os.getenv('NETKEIBA_NAR_TIMEOUT_SEC','3.5')),0 if force else 30)
    except Exception as exc:
        print('NAR netkeiba preview failed',rid,exc);return {}
    soup=BeautifulSoup(html,'html.parser');full=_clean(soup.get_text(' ',strip=True));forecast_page='予想オッズ' in full
    out={};field_count=0
    for tr in soup.select('tr.HorseList'):
        field_count+=1
        txt=_clean(tr.get_text(' ',strip=True));no=0
        um=tr.find('td',class_=re.compile(r'Umaban',re.I))
        if um:
            mm=re.search(r'\d{1,2}',_clean(um.get_text(' ',strip=True)));no=int(mm.group()) if mm else 0
        if not no:
            mm=re.match(r'\D*(\d{1,2})\D+',txt);no=int(mm.group(1)) if mm else 0
        if not no:continue
        odd=None;pop=None
        odds_span=tr.find('span',id=re.compile(r'^odds-1_'))
        ns=tr.find('span',id=re.compile(r'^ninki-1_'))
        if odds_span:
            mo=re.search(r'\d+(?:\.\d+)?',_clean(odds_span.get_text(' ',strip=True)));odd=float(mo.group()) if mo else None
        if ns:
            mp=re.search(r'\d+',_clean(ns.get_text(' ',strip=True)));pop=int(mp.group()) if mp else None
        if odd is None:
            mo=re.search(r'(?<!\d)(\d{1,3}(?:\.\d+)?)\s*[（(]\s*(\d{1,2})人気\s*[）)]',txt)
            if mo:odd=float(mo.group(1));pop=int(mo.group(2))
        bw=None;chg=None
        wt=tr.select_one('td.Weight')
        wtxt=_clean(wt.get_text(' ',strip=True)) if wt else txt
        bm=re.search(r'(?<!\d)(\d{3})\s*kg?\s*[（(]\s*([+\-]?\d+)\s*[）)]',wtxt)
        if not bm:bm=re.search(r'(?<!\d)(\d{3})\s*[（(]\s*([+\-]?\d+)\s*[）)]',wtxt)
        if bm:bw=int(bm.group(1));chg=int(bm.group(2))
        if odd is None and bw is None:continue
        z={}
        if odd and odd>1:
            z.update({'winOdds':odd,'popularity':pop,'oddsSource':'netkeiba予想オッズ' if forecast_page else 'netkeiba実オッズ','oddsForecast':bool(forecast_page)})
        if bw:
            z['bodyWeight']=bw;z['bodyWeightChange']=chg
        out[no]=z
    # v247: shutuba can omit the odds cells even while netkeiba's dedicated
    # NAR odds page already has them. Pull that page directly and merge the live
    # single-win odds so the full-day expected-value scan is not stuck at 0/N.
    field_count=max(field_count if 'field_count' in locals() else 0,len(out))
    have_odds=sum(1 for z in out.values() if (z or {}).get('winOdds'))
    if force or have_odds<max(3,int(max(1,field_count)*.65)):
        odds_url=f"https://nar.netkeiba.com/odds/index.html?race_id={rid}&type=b1"
        if force:odds_url+=f"&t={int(time.time()*1000)}"
        try:
            oh=_netkeiba_get(odds_url,float(os.getenv('NETKEIBA_NAR_ODDS_TIMEOUT_SEC','3.2')),0 if force else 12)
            osoup=BeautifulSoup(oh,'html.parser')
            for table in osoup.find_all('table'):
                headers=[_clean(x.get_text(' ',strip=True)).replace(' ','') for x in table.find_all('th')]
                if not headers:continue
                def hi(*parts):
                    for j,hv in enumerate(headers):
                        if any(p in hv for p in parts):return j
                    return -1
                ino=hi('馬番');iodd=hi('単勝オッズ','オッズ');ipop=hi('人気')
                if ino<0 or iodd<0:continue
                # Some tables include grouped/multi-row headers; use rows with enough td cells only.
                for tr in table.find_all('tr'):
                    cells=tr.find_all('td')
                    if not cells:continue
                    vals=[_clean(td.get_text(' ',strip=True)) for td in cells]
                    if max(ino,iodd)>=len(vals):continue
                    try:no=int(re.sub(r'\D','',vals[ino]) or 0)
                    except Exception:no=0
                    if no<=0 or no>30:continue
                    mo=re.search(r'\d+(?:\.\d+)?',vals[iodd].replace(',',''))
                    if not mo:continue
                    try:odd=float(mo.group())
                    except Exception:continue
                    if odd<=1:continue
                    pop=None
                    if 0<=ipop<len(vals):
                        mp=re.search(r'\d+',vals[ipop])
                        if mp:
                            try:pop=int(mp.group())
                            except Exception:pop=None
                    z=out.setdefault(no,{})
                    z['winOdds']=odd;z['oddsSource']='netkeiba実オッズ';z['oddsForecast']=False
                    if pop:z['popularity']=pop
        except Exception as exc:
            print('NAR netkeiba odds-page fallback failed',rid,exc)
    return out

def _netkeiba_current_result(detail:dict)->dict|None:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return None
    try:html=_netkeiba_get(f"https://race.netkeiba.com/race/result.html?race_id={rid}",float(os.getenv("NETKEIBA_RESULT_TIMEOUT_SEC","3.0")),20)
    except Exception as exc:
        print("netkeiba result failed",rid,exc);return None
    return _parse_netkeiba_result_html(
        html, clean=_clean, parse_time_seconds=_jra_parse_time_seconds,
        parse_payouts=_parse_payouts,
    )

def _netkeiba_race_meta(detail:dict)->dict:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return {}
    try:html=_netkeiba_get(f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}",float(os.getenv("NETKEIBA_DETAIL_TIMEOUT_SEC","3.5")),20)
    except Exception:return {}
    soup=BeautifulSoup(html,"html.parser");full=_clean(soup.get_text(" ",strip=True));out={}
    h1=soup.find("h1")
    if h1:out["title"]=_clean(h1.get_text(" ",strip=True))
    sm=re.search(r"(\d{1,2}:\d{2})発走",full)
    if sm:out["startTime"]=sm.group(1)
    dm=re.search(r"(?:芝|ダ|障)(\d{3,4})m",full)
    if dm:out["distance"]=int(dm.group(1))
    wm=re.search(r"天候[:：]?\s*(晴|曇|雨|小雨|雪|小雪)",full)
    if wm:out["weather"]=wm.group(1)
    cm=re.search(r"馬場[:：]?\s*(良|稍重|重|不良)",full)
    if cm:out["condition"]=cm.group(1)
    return out

def _smart_normalize_row(x:dict)->dict|None:
    if not isinstance(x,dict):return None
    no=_safe_int(_pick(x,"horseNumber","horse_no","uno","number","馬番")); name=str(_pick(x,"name","hname","horseName","馬名") or "").strip()
    if not no and not name:return None
    smart={"ten1f":_pick(x,"ten1f","ten1f_best","h1_ten1f","テン1F"),"ten":_pick(x,"ten","ten_pat","ten_has","テン"),"agari":_pick(x,"agari","agari3f","furlong3","agari_pat","agari_has","上がり"),"estimatedPopularity":_pick(x,"estimatedPopularity","est_pop","推人","推定人気")}
    out={"horseNumber":no,"name":name,"smartRc":smart}
    rr=_pick(x,"recentRaces","recent_races")
    if isinstance(rr,list):out["recentRaces"]=[z for z in rr if isinstance(z,dict)][:5]
    return out

def _extract_smartrc_embedded(html:str)->list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    for sc in soup.find_all("script"):
        raw=(sc.string or sc.get_text() or "").strip()
        if not raw or ("hname" not in raw and "horseNumber" not in raw and '"uno"' not in raw):continue
        candidates=[]
        if sc.get("type") in ("application/json","application/ld+json"):
            try:candidates.append(json.loads(raw))
            except Exception:pass
        for m in re.finditer(r"(?:=|:)\s*(\[[\s\S]{10,120000}?\]|\{[\s\S]{10,120000}?\})\s*;",raw):
            try:candidates.append(json.loads(html_lib.unescape(m.group(1))))
            except Exception:pass
        for c in candidates:
            rows=_json_horse_rows(c)
            if rows:return rows
    return []

def _fetch_smartrc(detail:dict)->dict:
    key=str(detail.get("id") or f"{detail.get('date')}|{detail.get('track')}|{detail.get('raceNumber')}");now=time.time()
    with _smart_cache_lock:
        hit=_smart_cache.get(key)
        if hit and now-hit[0]<600:return hit[1]
    feed=str(os.getenv("SMARTRC_FEED_URL","")).strip();token=str(os.getenv("SMARTRC_FEED_TOKEN","")).strip();out={"rows":[],"status":"browser","error":"","url":"https://www.smartrc.jp/v3/"}
    if feed:
        try:
            raw=_json_horse_rows(_fetch_json_url(_format_feed_url(feed,detail),float(os.getenv("SMARTRC_TIMEOUT_SEC","5")),token));rows=[z for z in (_smart_normalize_row(x) for x in raw) if z];out={"rows":rows,"status":"done" if rows else "unavailable","error":"","url":"https://www.smartrc.jp/v3/"}
        except Exception as exc:out={"rows":[],"status":"error","error":str(exc)[:220],"url":"https://www.smartrc.jp/v3/"}
    with _smart_cache_lock:_smart_cache[key]=(now,out)
    return out

def _fetch_extra_sources(detail:dict)->list[dict]:
    spec=str(os.getenv("EXTRA_RACE_FEEDS","")).strip(); out=[]
    if not spec:return out
    for part in spec.split(";"):
        part=part.strip()
        if not part:continue
        name,url=(part.split("=",1) if "=" in part else ("補助",part))
        try:
            body=_fetch_json_url(_format_feed_url(url.strip(),detail),float(os.getenv("EXTRA_FEED_TIMEOUT_SEC","4")),str(os.getenv("EXTRA_FEED_TOKEN","")).strip()); rows=[]
            for x in _json_horse_rows(body):
                no=_safe_int(_pick(x,"horseNumber","horse_no","uno","number","馬番"));hn=str(_pick(x,"name","hname","horseName","馬名") or "").strip()
                if no or hn:rows.append({"horseNumber":no,"name":hn,"extra":x})
            if rows:out.append({"source":name.strip() or "補助","rows":rows})
        except Exception as exc:print("extra source failed",name,exc)
    return out
