"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def iter_months_back(target: dt_date, count: int) -> Iterator[tuple[int, int]]:
    year, month = target.year, target.month
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        yield year, month

def sync_recent_history(months: int = 12) -> list[dict]:
    sync = NarSync()
    out = []
    today = datetime.now().date()
    for year, month in reversed(list(iter_months_back(today, months))):
        out.append(sync.sync_month(year, month))
    return out

def _history_worker(months_back: int | None = None):
    global _history_ready, _history_error
    # v43: do not block on-demand history behind an 18-month serial startup crawl.
    # Warm only the latest few months, in parallel. Deeper history is fetched only when needed.
    time.sleep(float(os.getenv("HISTORY_START_DELAY_SEC", "0.15")))
    today = datetime.now().date()
    if months_back is None:
        months_back = max(2, min(8, int(os.getenv("NAR_HISTORY_WARM_MONTHS", "4"))))
    seen = set()
    jobs = []
    for y, m in [(today.year, today.month)] + list(iter_months_back(today, months_back - 1)):
        if (y, m) not in seen:
            jobs.append((y, m)); seen.add((y, m))
    try:
        _, errors = _sync_nar_month_wave(jobs)
        _history_error = " | ".join(errors)
    except Exception as exc:
        _history_error = str(exc)
    _history_ready = True

def ensure_history_async():
    global _history_started
    with _history_lock:
        if _history_started:
            return
        _history_started = True
        threading.Thread(target=_history_worker, daemon=True).start()

@app.on_event("startup")
def _startup_history_backfill():
    # v43: targeted race prefetch is faster than a competing global crawl.
    if str(os.getenv("NAR_BACKGROUND_WARM", "0")).lower() in {"1","true","yes","on"}:
        ensure_history_async()

@app.post("/api/v1/history-backfill-one")
def history_backfill_one(months_ago: int = Query(1, ge=1, le=24)):
    target=datetime.now().date().replace(day=1)
    y,m=target.year,target.month
    for _ in range(months_ago):
        m-=1
        if m==0:y-=1;m=12
    def worker():
        try:NarSync().sync_month(y,m,force=False)
        except Exception as exc:print(f"manual history backfill failed: {exc}")
    threading.Thread(target=worker,daemon=True).start()
    return {"status":"started","year":y,"month":m}

@app.get("/api/v1/history-status")
def history_status():
    return {"started":_history_started,"ready":_history_ready,"error":_history_error}

def _nar_month_needs_fetch(year: int, month: int) -> bool:
    cache_key = f"month-{year:04d}-{month:02d}"
    store = NarStore()
    try:
        synced = store.synced_at(cache_key)
    finally:
        try: store.conn.close()
        except Exception: pass
    if not synced:
        return True
    today = datetime.now().date()
    if year == today.year and month == today.month:
        return int(time.time()) - synced >= int(os.getenv("NAR_CURRENT_MONTH_TTL_SECONDS", "300"))
    return False

def _download_nar_month_only(year: int, month: int) -> tuple[int, int, bytes, Path]:
    dest = ARCHIVE_DIR / f"{year:04d}{month:02d}_race.zip"
    url = NAR_MONTHLY_RACE_URL.format(year=year, month=month)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/zip,application/octet-stream,*/*",
            "Referer": "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            "Accept-Language": "ja-JP,ja;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=float(os.getenv("NAR_FAST_TIMEOUT_SEC", "22"))) as response:
        data = response.read()
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise RuntimeError(f"NAR {year:04d}-{month:02d} was not ZIP")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return year, month, data, dest

def _sync_nar_month_wave(months: list[tuple[int, int]]) -> tuple[list[dict], list[str]]:
    # Download network-bound monthly ZIPs concurrently, then import sequentially into SQLite.
    # This keeps DB writes safe while removing the largest source of wait time.
    unique = list(dict.fromkeys(months))
    need = [(y, m) for y, m in unique if _nar_month_needs_fetch(y, m)]
    results: dict[tuple[int, int], tuple[int, int, bytes, Path]] = {}
    errors: list[str] = []
    workers = max(2, min(6, int(os.getenv("NAR_HISTORY_WORKERS", "6"))))
    if need:
        with ThreadPoolExecutor(max_workers=min(workers, len(need))) as pool:
            future_map = {pool.submit(_download_nar_month_only, y, m):(y, m) for y, m in need}
            for fut in as_completed(future_map):
                y, m = future_map[fut]
                try:
                    results[(y, m)] = fut.result()
                except Exception as exc:
                    errors.append(f"{y:04d}-{m:02d}:{exc}")
    sync = NarSync()
    out = []
    try:
        for y, m in unique:
            if (y, m) not in results:
                out.append({"status":"cached","cacheKey":f"month-{y:04d}-{m:02d}"})
                continue
            _, _, data, dest = results[(y, m)]
            try:
                with _nar_sync_io_lock:
                    info = sync.import_zip_bytes(data, f"month-{y:04d}-{m:02d}", dest)
                out.append({"status":"synced", **info})
            except Exception as exc:
                errors.append(f"{y:04d}-{m:02d}:import:{exc}")
    finally:
        try: sync.store.conn.close()
        except Exception: pass
    return out, errors

def _months_from_race_date(iso_date: str, count: int):
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    y, m = d.year, d.month
    for _ in range(max(1, count)):
        yield y, m
        m -= 1
        if m == 0:
            y -= 1
            m = 12

def _history_counts(horse_names: list[str], cutoff: str) -> dict:
    names = [x for x in dict.fromkeys(horse_names) if x]
    if not names:
        return {"totalHorses":0,"horsesWithHistory":0,"horsesWith4Plus":0,"horsesWith5Plus":0,"horsesWith6Plus":0,"totalRuns":0,"counts":{},"underFive":[]}
    store = NarStore()
    try:
        placeholders = ",".join("?" for _ in names)
        rows = store.conn.execute(
            f"SELECT name,COUNT(*) cnt FROM entries WHERE name IN ({placeholders}) AND date<? AND finish>0 GROUP BY name",
            (*names, cutoff),
        ).fetchall()
        cmap = {r["name"]: int(r["cnt"] or 0) for r in rows}
    finally:
        try: store.conn.close()
        except Exception: pass
    counts = {name: int(cmap.get(name, 0)) for name in names}
    vals = list(counts.values())
    return {
        "totalHorses": len(names),
        "horsesWithHistory": sum(1 for v in vals if v > 0),
        "horsesWith4Plus": sum(1 for v in vals if v >= 4),
        "horsesWith5Plus": sum(1 for v in vals if v >= 5),
        "horsesWith6Plus": sum(1 for v in vals if v >= 6),
        "totalRuns": sum(vals),
        "counts": counts,
        "underFive": [name for name, v in counts.items() if v < 5],
    }

def _start_race_history_search(race_id: str, iso_date: str, horse_names: list[str], force: bool = False) -> dict:
    max_months = max(6, min(36, int(os.getenv("NAR_ON_DEMAND_HISTORY_MONTHS", "36"))))
    # Race-date-bound start counts may already be recorded in the prepared
    # snapshot. They are the lower bound the official local DB must cover.
    # An unknown count is NOT evidence that five runs exhaust the lifetime.
    try:
        original = RACEDB.get_race(race_id)[0]
    except Exception:
        original = None
    required = pre_race_reported_starts(original, iso_date, horse_names)
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        cov = _history_counts(horse_names, iso_date)
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"","source":"NAR公式月次レースデータ",
               "knownCareerStarts":len(required),"fullCareerVerified":official_history_complete(cov,required)}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        months = list(_months_from_race_date(iso_date, max_months))
        wave = max(2, min(4, int(os.getenv("NAR_ON_DEMAND_WAVE_MONTHS", "3"))))
        try:
            for pos in range(0, len(months), wave):
                batch = months[pos:pos+wave]
                # Bound cross-race NAR ZIP downloads; the SQL import itself
                # also retains the existing single-writer lock.
                with nar_history_wave_slots:
                    _, errs = _sync_nar_month_wave(batch)
                errors.extend(errs)
                months_done += len(batch)
                cov_now = _history_counts(horse_names, iso_date)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"NAR公式 高速並列履歴"}
                # Five runs are display data, not the complete career.
                # Stop only when every horse's official lifetime count for
                # this race date has been reached. Otherwise use the bounded
                # configured lookback, leaving coverage explicitly unverified.
                if official_history_complete(cov_now, required):
                    break
            cov_now = _history_counts(horse_names, iso_date)
            # This worker owns *only* the NAR official month ZIP/SQLite lane.
            # Full-career transfers and independent provider identity checks
            # belong to the canonical Full Prefetch enrichment pipeline.
            verified = official_history_complete(cov_now, required)
            status = "done" if verified else ("error" if errors and not cov_now.get("horsesWithHistory",0) else "partial")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,
                                               "coverage":cov_now,"error":" | ".join(errors[-5:]),
                                               "source":"NAR公式 高速並列履歴",
                                               "knownCareerStarts":len(required),"fullCareerVerified":verified}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
            try:_build_fast_diagnosis_snapshot(race_id,allow_network=False,deep_context=True)
            except Exception as exc:print("NAR history diagnosis rebuild failed",race_id,exc)
        except Exception as exc:
            errors.append(str(exc))
            cov_now = _history_counts(horse_names, iso_date)
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":"error","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"NAR公式 高速並列履歴"}
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)

def _race_history_status(race_id: str) -> dict | None:
    with _race_history_lock:
        x = _race_history_jobs.get(race_id)
        return dict(x) if x else None

def _start_central_history_search(race_id: str, iso_date: str, force: bool = False) -> dict:
    max_months = max(12, min(60, int(os.getenv("CENTRAL_ON_DEMAND_HISTORY_MONTHS", "36"))))
    detail = central_race_detail(race_id)
    cov = _central_detail_coverage(detail or {})
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        has_feed=bool(_clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) or _clean(os.getenv("CENTRAL_FEED_URL", "")))
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"",
               "source":"中央フィード高速並列検索" if has_feed else "JRA公式 競走馬情報5走補完"}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        store = CentralStore()
        try:
            # With no external central feed, use each horse's official JRA profile directly.
            if not has_feed:
                current=central_race_detail(race_id) or {}
                horses=current.get("horses") or []
                cutoff=current.get("date") or iso_date
                # The official profile page may contain far more than five
                # performances. Preserve its entire available pre-race career
                # in allPastRuns, keeping only recentRaces at five for the UI.
                history_limit=max(6,min(1000,int(os.getenv("ARVEXQ_CAREER_FETCH_LIMIT","1000"))))
                def fill(h):
                    h=dict(h)
                    try:
                        cname=h.get("_jraHorseCname") or h.get("jraHorseCname") or ""
                        extra=_jra_profile_runs(cname,cutoff,history_limit)
                        h=merge_full_profile_history(h,extra,cutoff)
                    except Exception as exc:
                        errors.append(str(exc))
                    return h
                workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:
                    current["horses"]=list(pool.map(fill,horses)) if horses else []
                current["source"]="JRA公式"
                store.upsert([current])
                fresh_detail=central_race_detail(race_id) or current
                cov_now=_central_detail_coverage(fresh_detail)
                total_now=int(cov_now.get("totalHorses") or 0)
                resolved_now=int(cov_now.get("horsesResolved") or cov_now.get("horsesWith5Plus") or 0)
                # A debut/young horse can legitimately have 0 prior runs. If JRA says the
                # inspected career is complete, treat it as resolved instead of a fetch error.
                central_done=bool(assess_career_readiness(fresh_detail).get("ready"))
                with _race_history_lock:
                    _race_history_jobs[race_id]={"status":"done" if central_done else ("error" if errors and not cov_now.get("horsesWithHistory",0) else "partial"),
                        "monthsDone":0,"maxMonths":0,"coverage":cov_now,"error":" | ".join(errors[-5:]),
                        "source":"JRA公式 競走馬情報全過去走補完","fullCareerVerified":central_done}
                with _detail_cache_lock:
                    _detail_cache.pop(race_id,None)
                return
            for y, m in _months_from_race_date(iso_date, max_months):
                days = _central_month_dates(y, m, iso_date)
                fresh_rows, errs = _fetch_central_days_parallel(days)
                errors.extend(errs)
                if fresh_rows:
                    store.upsert(fresh_rows)
                months_done += 1
                fresh_detail = central_race_detail(race_id) or {}
                cov_now = _central_detail_coverage(fresh_detail)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,
                                                   "coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"中央フィード高速並列検索"}
                if assess_career_readiness(fresh_detail).get("ready"):
                    break
            fresh_detail = central_race_detail(race_id) or {}
            cov_now = _central_detail_coverage(fresh_detail)
            verified=bool(assess_career_readiness(fresh_detail).get("ready"))
            status = "done" if verified else ("error" if errors and not cov_now.get("horsesWithHistory",0) else "partial")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,
                                               "coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"中央フィード高速並列検索",
                                               "fullCareerVerified":verified}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
        finally:
            try:
                store.conn.close()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)
