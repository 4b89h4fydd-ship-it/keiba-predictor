"""supplemental/enrichment: original PR #13 acquisition orchestration.

Storage, evaluation and provider callbacks are explicit keyword-only ports.
Worker behavior, source priority and immutable prediction handling are preserved.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time



from arvexq.ingest.supplemental.state import _enrich_data
from arvexq.ingest.supplemental.state import _enrich_data_lock
from arvexq.ingest.supplemental.state import _enrich_jobs
from arvexq.ingest.supplemental.state import _enrich_jobs_lock

def _enrichment_status(race_id: str) -> dict:
    with _enrich_jobs_lock:
        st=_enrich_jobs.get(race_id);return dict(st) if st else {"status":"idle","sources":[],"error":""}



def _start_enrichment(race_id: str, detail: dict, force: bool=False, horse_no: int | None=None, *, PREPARED_STORE, RACEDB, _attach_evaluation_context, _attach_stored_career, _detail_cache, _detail_cache_lock, _enrichment_status, _fetch_extra_sources, _merge_enrichment, _netkeiba_detail_rows, _precompute_detail_metrics) -> dict:
    now=time.time()
    with _enrich_jobs_lock:
        old=_enrich_jobs.get(race_id)
        if old and old.get("status")=="running" and not force:return dict(old)
        if old and old.get("status") in {"done","unavailable"} and not force and now-float(old.get("finishedAt") or 0)<300:return dict(old)
        _enrich_jobs[race_id]={"status":"running","sources":[],"error":"","startedAt":now,"horseNumber":horse_no}
    snap=json.loads(json.dumps(detail,ensure_ascii=False,default=str))
    def worker():
        errs=[];sources=[];netkeibaRows=[];smartRows=[];extra=[]
        def get_netkeiba():
            if snap.get("circuit")!="中央":return []
            try:return _netkeiba_detail_rows(snap)
            except Exception as exc:errs.append("netkeiba: "+str(exc));return []
        def get_smart():
            # v146: SmartRc tempo/final-section metrics are intentionally suspended.
            return []
        def get_extra():
            try:return _fetch_extra_sources(snap)
            except Exception as exc:errs.append("補助: "+str(exc));return []
        try:
            with ThreadPoolExecutor(max_workers=3) as pool:
                f_net=pool.submit(get_netkeiba);f_smart=pool.submit(get_smart);f_extra=pool.submit(get_extra)
                netkeibaRows=f_net.result() or [];smartRows=f_smart.result() or [];extra=f_extra.result() or []
            if netkeibaRows:sources.append("netkeiba")
            if smartRows:sources.append("SmartRc")
            for b in extra:
                if b.get("source") not in sources:sources.append(b.get("source"))
        except Exception as exc:errs.append("情報取得: "+str(exc))
        if horse_no:
            netkeibaRows=[x for x in netkeibaRows if int(x.get("horseNumber") or 0)==int(horse_no)]
            smartRows=[x for x in smartRows if int(x.get("horseNumber") or 0)==int(horse_no)]
        with _enrich_data_lock:
            olddata=_enrich_data.get(race_id) or {}
            nk={}
            for rr in (olddata.get("netkeibaRows") or [])+netkeibaRows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                nk[key]=rr
            sk={}
            for rr in (olddata.get("smartRows") or [])+smartRows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                sk[key]=rr
            _enrich_data[race_id]={"netkeibaRows":list(nk.values()),"smartRows":list(sk.values()),"extra":extra or olddata.get("extra") or []}
        with _enrich_jobs_lock:_enrich_jobs[race_id]={"status":"done" if sources else "unavailable","sources":sources,"error":" | ".join(errs[-3:]),"finishedAt":time.time(),"horseNumber":horse_no}
        try:
            enriched=json.loads(json.dumps(snap,ensure_ascii=False,default=str))
            with _enrich_data_lock:
                saved_data=_enrich_data.get(race_id) or {}
            enriched=_merge_enrichment(enriched,saved_data)
            enriched["enrichmentSearch"]=_enrichment_status(race_id)
            latest,_=PREPARED_STORE.get(race_id)
            if latest:
                enriched=_merge_enrichment(latest,saved_data)
                enriched["enrichmentSearch"]=_enrichment_status(race_id)
            enriched=_precompute_detail_metrics(_attach_evaluation_context(_attach_stored_career(enriched)))
            PREPARED_STORE.put(enriched)
            RACEDB.upsert_race(enriched)
        except Exception as exc:print("RaceDB enrichment save failed",race_id,exc)
        with _detail_cache_lock:_detail_cache.pop(race_id,None)
    threading.Thread(target=worker,daemon=True).start();return _enrichment_status(race_id)



def _apply_enrichment(race_id: str, detail: dict, *, _enrichment_status, _merge_enrichment) -> dict:
    with _enrich_data_lock:data=_enrich_data.get(race_id)
    if data:_merge_enrichment(detail,data)
    detail["enrichmentSearch"]=_enrichment_status(race_id)
    title=str(detail.get("title") or "");surface=str(detail.get("surface") or "")
    mode="障害" if (surface=="障害" or "障害" in title or re.search(r"(?:J[･・.]?G[ⅠⅡⅢ123]|\\bJS\\b|ジャンプ)",title,re.I)) else ("新馬" if re.search(r"(?:新馬|メイクデビュー)",title) else "平地")
    detail["analysisMode"]=mode
    if mode=="新馬":
        for h in detail.get("horses",[]) or []:
            if not (h.get("recentRaces") or []):h["debutNoHistory"]=True
    return detail
