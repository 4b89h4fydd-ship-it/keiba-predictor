"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_result_cname_from_card(cname:str)->str:
    if not cname:return ""
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20)
    except Exception as exc:
        print("JRA result link fetch failed",exc);return ""
    vals=[_jra_norm_cname(x) for x in JRA_RESULT_CNAME_RE.findall(html)]
    return vals[0] if vals else ""

def _jra_prior_result_cnames(iso_date: str, track: str) -> list[str]:
    if track not in JRA_TRACK_CODE_BY_NAME or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", iso_date):
        return []
    month = iso_date[:7].replace("-", "")
    key = (iso_date, track)
    with _jra_prior_lookup_lock:
        if key in _jra_prior_meeting_cache:
            return list(_jra_prior_meeting_cache[key])
        if month not in _jra_prior_month_cache:
            home = _jra_request("https://www.jra.go.jp/", None, 86400)
            seed = re.search(r"doAction\('/JRADB/accessS.html',\s*'(pw01skl[^']+)'", home)
            if not seed:
                raise ValueError("JRA past-results menu link absent")
            menu = _jra_request("https://www.jra.go.jp/JRADB/accessS.html", seed.group(1), 86400)
            published = dict(re.findall(r'objParam\["(\d{4})"\]="([0-9A-Fa-f]{2})"', menu))
            current = re.search(r'var\s+yearMonth\s*=\s*"(\d{6})"', menu)
            if month[2:] not in published or not current:
                raise ValueError("JRA month selector token absent for " + month)
            selector = "pw01skl" + ("00" if month >= current.group(1) else "10") + month + "/" + published[month[2:]]
            _jra_prior_month_cache[month] = _jra_request("https://www.jra.go.jp/JRADB/accessS.html", selector, 86400)
        html = _jra_prior_month_cache[month]
        token = iso_date.replace("-", "")
        code = JRA_TRACK_CODE_BY_NAME[track]
        links = list(dict.fromkeys(_jra_norm_cname(x) for x in re.findall(
            r"pw01srl(?:01|10)\d{18}(?:/|%2F)[0-9A-Fa-f]{2}", html, re.I)))
        meetings = [x for x in links if x.startswith("pw01srl10" + code) or x.startswith("pw01srl01" + code)]
        meetings = [x for x in meetings if token + "/" in x]
        if len(meetings) != 1:
            return []
        page = _jra_request("https://www.jra.go.jp/JRADB/accessS.html", meetings[0], 86400)
        results = list(dict.fromkeys(_jra_norm_cname(x) for x in JRA_RESULT_CNAME_RE.findall(page)))
        results = [x for x in results if _jra_date_from_cname(x) == iso_date and _jra_any_track(x) == track]
        if not results:
            raise ValueError("JRA meeting returned no result links: " + meetings[0])
        soup = BeautifulSoup(page, "html.parser")
        for tr in soup.select("#race_list tbody tr"):
            link = _jra_attr_cname(tr, JRA_RESULT_CNAME_RE)
            distance = re.search(r"[\d,]+", _jra_text(tr.select_one(".dist")))
            if link and distance:
                _jra_prior_result_meta[link] = {"distance": int(distance.group().replace(",", "")),
                                              "surface": _jra_text(tr.select_one(".course"))}
        _jra_prior_meeting_cache[key] = results
        return list(results)

def _jra_resolve_prior_results(horse: dict, run: dict) -> dict | None:
    """Resolve a source-less start by observed identity, never by inferred time."""
    import unicodedata
    def clean(value):
        return "".join(unicodedata.normalize("NFKC", str(value or "")).split())
    at = str(run.get("date") or "")
    track = str(run.get("track") or "")
    name = clean(horse.get("name"))
    cnames = _jra_prior_result_cnames(at, track)
    no = int(run.get("raceNumber") or 0)
    if no:
        cnames = [c for c in cnames if _jra_any_race_no(c) == no]
    if run.get("distance"):
        cnames = [c for c in cnames if not _jra_prior_result_meta.get(c) or
                  _jra_prior_result_meta[c]["distance"] == int(run["distance"])]
    def surface(value):
        return "障害" if "障" in value or "→" in value else "芝" if "芝" in value else "ダート" if "ダ" in value else ""
    if surface(str(run.get("surface") or "")):
        cnames = [c for c in cnames if not _jra_prior_result_meta.get(c) or
                  surface(_jra_prior_result_meta[c]["surface"]) == surface(str(run["surface"]))]
    matches = []
    for cname in cnames:
        with _jra_prior_lookup_lock:
            lock = _jra_prior_result_locks.setdefault(cname, threading.Lock())
        with lock:
            if cname not in _jra_prior_parsed_cache:
                result = None
                for attempt in range(2):
                    try:
                        result = _jra_parse_result(cname, strict_errors=True)
                        break
                    except Exception as exc:
                        if attempt == 1:
                            raise
                        print("JRA_PRIOR_RESULT_RETRY", cname, type(exc).__name__, flush=True)
                        time.sleep(.3)
                if not isinstance(result, dict):
                    raise ValueError("JRA official prior result parse failed: " + cname)
                _jra_prior_parsed_cache[cname] = result
            result = _jra_prior_parsed_cache[cname]
        if result.get("date") != at or result.get("track") != track:
            continue
        if run.get("distance") and int(result.get("distance") or 0) != int(run["distance"]):
            continue
        rows = [r for r in (result.get("result") or {}).get("finishers") or [] if clean(r.get("name")) == name]
        if len(rows) != 1:
            continue
        row = rows[0]
        if run.get("finish") and int(row.get("finish") or 0) != int(run["finish"]):
            continue
        if run.get("timeSeconds") and abs(float(run["timeSeconds"]) - float(row.get("timeSeconds") or 0)) > .11:
            continue
        matches.append(result)
    return matches[0] if len(matches) == 1 else None

def _race_should_have_result(detail:dict)->bool:
    d=str(detail.get("date") or ""); st=str(detail.get("startTime") or "")
    if not d:return False
    today=_today_iso()
    if d<today:return True
    if d>today:return False
    m=re.match(r"(\d{1,2}):(\d{2})",st)
    if not m:return False
    start=int(m.group(1))*60+int(m.group(2)); nowj=_now_jst(); now=nowj.hour*60+nowj.minute
    return now>=start+3

def _data_core_result_due(detail:dict)->bool:
    try:
        if str(detail.get("date") or "")!=_today_iso():return True
        st=_race_minutes_server(detail)
        if st>=9999:return False
        now=_now_jst();return now.hour*60+now.minute>=st+2
    except Exception:return False

def _result_has_podium(detail: dict | None) -> bool:
    result=(detail or {}).get("result") or {}
    ranks={int(x.get("finish") or 0) for x in (result.get("finishers") or []) if isinstance(x,dict)}
    return all(i in ranks for i in (1,2,3))

def _refresh_result_fast(race_id: str) -> dict | None:
    """Refresh only authoritative result data; never rebuild history/diagnosis."""
    detail=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not detail:
        detail=nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:return None

    official=None
    if race_id.startswith("nar-"):
        try:official=_nar_official_result_fast(detail)
        except Exception as exc:print("NAR fast result refresh failed",race_id,exc)
        if official:
            detail["result"]=official
            if official.get("weather") not in (None,"","不明"):detail["weather"]=official["weather"]
            if official.get("condition") not in (None,"","不明"):detail["condition"]=official["condition"]
            detail=_merge_result_fields(detail,official)
        elif _race_should_have_result(detail):
            try:
                nk=_netkeiba_current_result(detail)
                if nk:
                    detail["result"]=nk
                    detail=_merge_result_fields(detail,nk)
            except Exception as exc:print("NAR result fallback failed",race_id,exc)
        if _result_has_podium(detail):
            try:detail=_attach_nar_payouts(detail)
            except Exception as exc:print("NAR payout attach after result failed",race_id,exc)
    else:
        try:
            result_cname=str(detail.get("resultCname") or "")
            if not result_cname:
                cname=_jra_find_cname(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
                if cname:result_cname=_jra_result_cname_from_card(cname)
            parsed=_jra_parse_result(result_cname,detail) if result_cname else None
            if parsed:detail=_merge_official_result(detail,parsed)
        except Exception as exc:print("JRA fast result refresh failed",race_id,exc)
        if not _result_has_podium(detail) and _race_should_have_result(detail):
            try:
                nk=_netkeiba_current_result(detail)
                if nk:
                    detail["result"]=nk
                    detail=_merge_result_fields(detail,nk)
            except Exception as exc:print("JRA result fallback failed",race_id,exc)

    if _result_has_podium(detail):
        try:_store_fast_snapshot(detail)
        except Exception as exc:print("result snapshot save failed",race_id,exc)
    return _compact_display_snapshot(detail)

def _nar_result_should_be_available(detail:dict, grace_min:int=1)->bool:
    date=str(detail.get("date") or "")
    if not date:return False
    if date<_today_iso():return True
    if date>_today_iso():return False
    st=str(detail.get("startTime") or detail.get("scheduledStartTime") or "")
    m=re.match(r"^(\d{1,2}):(\d{2})",st)
    if not m:return False
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    return nowm>=int(m.group(1))*60+int(m.group(2))+int(grace_min)
