from arvexq.components.runtime import install_component
from arvexq.services import prepare_race_detail
from arvexq.ingest.pure_parsers import (
    decode_csv_bytes,
    _jra_decode,
    _decode_site,
    _json_horse_rows,
    _pick,
    _jra_run_key,
    _jra_run_value_present,
)
from arvexq.prediction.pure_diagnostics import (
    _central_detail_coverage,
    _diagnosis_history_quality,
    _audit_axes_from_eval,
    _learning_date_split,
    _pc_time_index,
    _prob_vector,
    _history_is_enough,
    _pc_season,
    _reference_weight_from_horse,
)
from arvexq.infra.pure_snapshots import (
    _bundle_quality,
    _racedb_snapshot_usable,
    _merge_official_result,
)
from arvexq.databanks.legacy_bridge import register_legacy_sources
from arvexq.ingest.nar_career_coverage import pre_race_reported_starts, official_history_complete, nar_history_wave_slots
from arvexq.ingest.jra_career_merge import merge_full_profile_history
from arvexq.prediction.career_readiness import assess_career_readiness
from arvexq.ui.assets import read_asset, read_binary_asset
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ARVEXQ Python source
from fastapi import FastAPI, Query, Request, HTTPException
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, Response, JSONResponse
import json
import math
import base64
import calendar
import csv
import hashlib
import io
import html as html_lib
import os
import unicodedata
import re
import sqlite3
import threading
import time
import urllib.request
import urllib.parse
import zipfile
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from datetime import date as dt_date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable, Iterator
from bs4 import BeautifulSoup
from arvexq.ingest.entry_fields.affiliation import from_text as observed_affiliation

app = FastAPI(title="ARVEXQ", version="14.26-v330-racecard-stable")
app.add_middleware(GZipMiddleware, minimum_size=900, compresslevel=5)

PREDICTION_ENGINE_VERSION = "arvexq-mineta-margin-observed-60-40-v1"
ARVEXQ_DATA_CORE_VERSION = "arvexq-data-core-v300-final"
AI_EVALUATION_VERSION = "evidence-v317-consensus-rebuild"
VOLATILITY_ENGINE_VERSION = "arvexq-volatility-v1"

from arvexq.prediction.course_speed_baselines import (
    V215_SPEED_BASE_EXACT, V215_SPEED_BASE_TRACK_DISTANCE,
    V215_SPEED_BASE_DISTANCE_GOING, V215_SPEED_GLOBAL,
)



install_component(200, "_arvexq_timing", globals())

INDEX = read_asset("index.html")

CSS = read_asset("styles.css")






















































JS = read_asset("app.js")
from arvexq.ui.bundle import compose_app_script
JS = compose_app_script(JS)

MANIFEST = r'''{
  "name":"ARVEXQ",
  "short_name":"ARVEXQ",
  "description":"ARVEXQ — PACE · POSITION · VALUE",
  "start_url":"/?pwa=1&v=329",
  "id":"/arvexq-v175-install",
  "icons":[{"src":"/arvexq-icon-v175-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"/arvexq-icon-v175-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}],
  "scope":"/",
  "display":"standalone",
  "background_color":"#f6f2e8",
  "theme_color":"#f6f2e8",
  "lang":"ja"
}'''
SW = r'''const RESET_TAG="arvexq-reset-v330";
self.addEventListener("install",function(event){event.waitUntil(self.skipWaiting())});
self.addEventListener("activate",function(event){
  event.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.map(function(k){return caches.delete(k)}));
  }).then(function(){return self.clients.claim()}));
});
// v319 reset worker does not intercept requests. Network is authoritative after deployment.
'''

HERO_HORSE_WEBP = base64.b64decode('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')
ARVEXQ_LOGO_WEBP = read_binary_asset("arvexq-logo-webp.webp")
PACE_PREVIEW_WEBP = read_binary_asset("pace-preview-webp.webp")

# --- NAR official live data connector ---------------------------------
NAR_DAILY_RACE_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"
NAR_MONTHLY_RACE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload"
    "?type=monthly&k_year={year}&k_month={month}"
)

install_component(140, "_default_data_root", globals())

DATA_ROOT = _default_data_root()
ARCHIVE_DIR = DATA_ROOT / "nar" / "archives"
DB_PATH = DATA_ROOT / "nar" / "nar.sqlite3"
PREPARED_DB_PATH = DATA_ROOT / "prepared" / "prepared.sqlite3"
RACEDB_PATH = Path(os.getenv("RACEDB_PATH", str(DATA_ROOT / "racedb" / "racedb.sqlite3")))
DAY_BUNDLE_DB_PATH = Path(os.getenv("DAY_BUNDLE_DB_PATH", str(DATA_ROOT / "bundle" / "day_bundle.sqlite3")))

from arvexq.ingest.nar_csv import RACE_IDX, HORSE_IDX, _stable_id, read_csv_from_zip, strip_header

from arvexq.ingest.field_normalization import (
    _clean, _int, _float, _carried_weight, _iso_date, _start_time, _time_seconds,
    _normalize_sex, _scratch_status, _normalize_weather, _normalize_condition,
)

from arvexq.ingest.corner_order import _top_level_tokens, parse_corner_order


install_component(140, "RaceRow", globals())


install_component(140, "EntryRow", globals())


# ARVEXQ_EXTRACTED:install_legacy_stores
from arvexq.infra.legacy_stores import install_legacy_stores as _arvexq_installer
_arvexq_installer(globals())
del _arvexq_installer


install_component(8, "normalize_central_race", globals())


JRA_TRACK_CODES = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
JRA_TRACK_CODE_BY_NAME = {v:k for k,v in JRA_TRACK_CODES.items()}
JRA_MEETING_DAY_RE = re.compile(r"(\d+)回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)(\d+)日")
JRA_CNAME_RE = re.compile(r"pw01dde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_HORSE_CNAME_RE = re.compile(r"pw01dud\d{12,}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_RESULT_CNAME_RE = re.compile(r"pw01sde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
_jra_cache_lock = threading.Lock()
_jra_text_cache: dict[str, tuple[float,str]] = {}

install_component(20, "_jra_request", globals())

install_component(20, "_jra_norm_cname", globals())

install_component(20, "_jra_attr_cname", globals())

JRA_BAD_TITLE_RE = re.compile(r"検索ウィンドウ|緊急情報|重要なお知らせ|お知らせ|関連メニュー|今週の開催|JRAからのお知らせ|インフォメーション|ピックアップ|発売レース|各種サービス|スペシャルコンテンツ|競馬メニュー|開催日程")
JRA_PROGRAM_TRACK_RE = re.compile(r"\d+回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\d+日")
_jra_program_cache_lock=threading.Lock(); _jra_program_cache={}
_jra_cname_lookup_lock=threading.Lock(); _jra_cname_lookup={}

install_component(20, "_jra_program_title", globals())

from arvexq.ingest.race_fields.meeting_schedule import extract as jra_meeting_schedule
from arvexq.ingest.race_fields.grade_class import extract as jra_grade_class

install_component(10, "_jra_program_summaries", globals())

install_component(10, "_jra_program_lookup", globals())

install_component(20, "_jra_find_cname", globals())

install_component(20, "_jra_text", globals())

from arvexq.ingest.jra_time import _jra_iso_date, _jra_parse_time_seconds

from arvexq.ingest.jra_identifiers import _jra_date_from_cname, _jra_race_no_from_cname

from arvexq.ingest.race_fields.track import extract as jra_race_track

install_component(9, "_jra_track_from_cname", globals())

from arvexq.ingest.past_fields.jra import parse_jra_history_cell

install_component(42, "_jra_parse_past_cell", globals())

install_component(57, "_jra_profile_runs", globals())

install_component(55, "_jra_merge_run_fields", globals())


install_component(57, "_jra_run_core_complete", globals())


install_component(57, "_jra_history_complete", globals())


install_component(55, "_jra_merge_runs", globals())

from arvexq.ingest.race_fields.start_time import extract as jra_start_time
from arvexq.ingest.race_fields.course import extract as jra_course
from arvexq.ingest.race_fields.distance import extract as jra_distance
from arvexq.ingest.race_fields.surface import extract as jra_surface
from arvexq.ingest.race_fields.prize import extract_first_prize as jra_first_prize

from arvexq.ingest.race_fields.title import extract as jra_race_title
from arvexq.ingest.race_fields.field_size import extract as jra_race_field_size

from arvexq.ingest.jra_official_table import select_runners_table as select_jra_runners_table
from arvexq.ingest.jra_official_runner_row import extract as jra_runner_row_number
from arvexq.ingest.jra_environment_parser import _parse_jra_environment_html
from arvexq.ingest.race_summary_merge import (
    index_summaries as _index_race_summaries,
    merge_refreshed_summaries as _merge_race_summaries,
    choose_card_identifiers as _choose_race_cards,
)

install_component(20, "_jra_parse_race", globals())

install_component(20, "_jra_parse_race_summary", globals())

install_component(20, "fetch_jra_official", globals())

install_component(22, "fetch_central_feed", globals())

install_component(154, "iter_months_back", globals())


install_component(154, "sync_recent_history", globals())


_nar_sync_io_lock = threading.Lock()
_history_lock = threading.Lock()
_history_started = False
_history_ready = False
_history_error = ""

install_component(154, "_history_worker", globals())

install_component(154, "ensure_history_async", globals())

install_component(200, "_now_jst", globals())

install_component(200, "_today_iso", globals())


install_component(154, "_startup_history_backfill", globals())


install_component(171, "storage_status", globals())


install_component(172, "health", globals())

install_component(154, "history_backfill_one", globals())

install_component(154, "history_status", globals())

install_component(162, "central_status", globals())

install_component(151, "central_ingest", globals())

install_component(162, "central_schema", globals())

_live_refresh_lock = threading.Lock()
_live_refresh_last: dict[str, int] = {}
_live_refresh_running: set[str] = set()

install_component(152, "_schedule_live_refresh", globals())


_central_refresh_lock = threading.Lock()
_central_refresh_running: set[str] = set()
_central_refresh_last: dict[str, int] = {}

install_component(152, "_schedule_central_refresh", globals())


_commercial_collector_lock=threading.Lock()
_commercial_collector_state={
    "running":False,"lastStart":0,"lastFinish":0,"lastError":"",
    "hydrated":0,"diagnosed":0,"cycleSec":0,
}

from arvexq.pipeline.race_priority import _race_minutes, _commercial_target_rows


install_component(152, "_commercial_collect_once", globals())

install_component(152, "_commercial_collector_loop", globals())

install_component(152, "_start_commercial_collector", globals())

install_component(172, "runtime_status", globals())

install_component(162, "collector_status", globals())

install_component(162, "_central_refresh_status", globals())

install_component(154, "_nar_month_needs_fetch", globals())


install_component(154, "_download_nar_month_only", globals())


install_component(154, "_sync_nar_month_wave", globals())


_race_history_lock = threading.Lock()
_race_history_jobs: dict[str, dict] = {}

install_component(154, "_months_from_race_date", globals())

install_component(154, "_history_counts", globals())

install_component(154, "_start_race_history_search", globals())

install_component(154, "_race_history_status", globals())

install_component(140, "_new_conn", globals())


install_component(163, "nar_race_summaries", globals())



NETKEIBA_TRACK_CODES={"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
_netkeiba_cache_lock=threading.Lock(); _netkeiba_cache={}

install_component(22, "_netkeiba_get", globals())

install_component(22, "_netkeiba_race_summaries", globals())

install_component(22, "_netkeiba_program_race_id", globals())

install_component(22, "_netkeiba_race_id", globals())

from arvexq.ingest.recent_result_cell import _parse_recent_cell



from arvexq.ingest.entry_fields.horse_number import _nk_row_horse_no


from arvexq.ingest.entry_fields.frame_number import _nk_row_frame


from arvexq.ingest.entry_fields.netkeiba import parse_row as _nk_row_horse




install_component(22, "_netkeiba_detail_rows", globals())

install_component(163, "central_race_summaries", globals())

NAR_BABA_CODES={"帯広ば":"03","帯広":"03","盛岡":"10","水沢":"11","浦和":"18","船橋":"19","大井":"20","川崎":"21","金沢":"22","笠松":"23","名古屋":"24","園田":"27","姫路":"28","高知":"31","佐賀":"32","門別":"36"}
NAR_NETKEIBA_CODES={"門別":"30","盛岡":"35","水沢":"36","浦和":"42","船橋":"43","大井":"44","川崎":"45","金沢":"46","笠松":"47","名古屋":"48","園田":"50","姫路":"51","高知":"54","佐賀":"55"}

install_component(22, "_nar_netkeiba_race_id", globals())

install_component(22, "_nar_netkeiba_preview_rows", globals())

_nar_odds_cache_lock=threading.Lock()
_nar_odds_cache:dict[str,tuple[float,dict]]={}

from arvexq.ingest.place_odds import place_odds_pair

from arvexq.ingest.nar_odds import parse_live_odds_html as _parse_nar_odds_html


install_component(64, "_parse_nar_live_odds_html", globals())


install_component(64, "_nar_live_odds", globals())

from arvexq.ingest.odds_capture_time import odds_observed_at

from arvexq.ingest.odds_fields.missing import odds_missing
from arvexq.ingest.odds_fields.delta import win_odds_delta

install_component(64, "_attach_nar_live_odds", globals())

install_component(164, "nar_race_detail", globals())




install_component(57, "_nar_attach_recent_batch", globals())


from arvexq.ingest.horse_identity import _horse_key


install_component(57, "_central_find_horse", globals())


install_component(57, "_central_run_from_race", globals())


install_component(57, "_central_resolve_race_id", globals())


install_component(57, "_central_recent_from_store", globals())


install_component(57, "_merge_central_recent", globals())


install_component(57, "_central_month_dates", globals())


install_component(57, "_fetch_central_days_parallel", globals())


install_component(154, "_start_central_history_search", globals())



from arvexq.ingest.netkeiba_odds_parser import _parse_netkeiba_win_odds_payload

install_component(65, "_netkeiba_live_win_odds", globals())

from arvexq.ingest.odds_results_merge import _merge_central_odds, _merge_result_fields

from arvexq.ingest.payouts import parse_payouts as _parse_payouts


install_component(85, "_fetch_nar_payouts_only", globals())


install_component(85, "_attach_nar_payouts", globals())


from arvexq.ingest.netkeiba_result import parse_current_result_html as _parse_netkeiba_result_html


install_component(22, "_netkeiba_current_result", globals())

install_component(153, "_jra_result_cname_from_card", globals())

install_component(20, "_jra_any_track", globals())

install_component(20, "_jra_any_race_no", globals())

# The historical result menu publishes month tokens (objParam) and meeting links.
# Use those actual official links when D1's original source has no horse cname.
_jra_prior_lookup_lock = threading.RLock()
_jra_prior_month_cache = {}
_jra_prior_meeting_cache = {}
_jra_prior_parsed_cache = {}
_jra_prior_result_meta = {}
_jra_prior_result_locks = {}

install_component(153, "_jra_prior_result_cnames", globals())

install_component(153, "_jra_resolve_prior_results", globals())


from arvexq.ingest.jra_result import parse_result_html as _parse_jra_result_html


install_component(20, "_jra_parse_result", globals())

install_component(22, "_netkeiba_race_meta", globals())

install_component(153, "_race_should_have_result", globals())

install_component(164, "central_race_detail", globals())

# --- v68 compact rows + fast JRA summaries; official data stays authoritative ---
_smart_cache_lock=threading.Lock(); _smart_cache:dict[str,tuple[float,dict]]={}
_enrich_jobs_lock=threading.Lock(); _enrich_jobs:dict[str,dict]={}
_enrich_data_lock=threading.Lock(); _enrich_data:dict[str,dict]={}

from arvexq.ingest.environment_values import _safe_float, _safe_int

install_component(22, "_smart_normalize_row", globals())

from arvexq.ingest.enrichment_transport import _format_feed_url, _fetch_json_url


install_component(22, "_extract_smartrc_embedded", globals())

install_component(22, "_fetch_smartrc", globals())

install_component(22, "_fetch_extra_sources", globals())

install_component(40, "_merge_enrichment", globals())

install_component(162, "_enrichment_status", globals())

install_component(40, "_start_enrichment", globals())

install_component(40, "_apply_enrichment", globals())



# --- v123 live weather / going -----------------------------------------
_environment_lock=threading.Lock()
_environment_running:set[str]=set()
_environment_state:dict[str,dict]={}
_environment_http_lock=threading.Lock()
_environment_http_cache:dict[str,tuple[float,dict]]={}

from arvexq.ingest.environment_values import _env_clean_weather, _env_clean_condition

from arvexq.ingest.nar_environment_parser import _parse_nar_environment_html

from arvexq.ingest.jra_environment_parser import _parse_jra_environment_html

install_component(157, "_environment_http_get", globals())

install_component(157, "_nar_fetch_environment", globals())

install_component(157, "_jra_fetch_environment", globals())

from arvexq.pipeline.race_clock import _race_minutes_server

install_component(157, "_upcoming_rows", globals())

install_component(157, "_patch_nar_environment", globals())

install_component(157, "_patch_central_environment", globals())

install_component(157, "_refresh_track_environment", globals())

install_component(157, "_schedule_track_environment", globals())

install_component(157, "_environment_cycle", globals())

install_component(157, "_environment_loop", globals())

install_component(157, "_start_environment_collector", globals())


# --- v82 prepared-race cache -------------------------------------------
# Race pages should not rebuild every horse's history/stat profile at tap time.
# We prepare complete display JSON in the background and serve that snapshot first.


from arvexq.ingest.horse_measurements import (_safe_body_weight_value, _safe_carried_weight_value, _sanitize_horse_measurements)


PRERACE_AUDIT_VERSION = "arvexq-prerace-audit-v317-consensus-rebuild"
WINNER_LEARNING_VERSION = "arvexq-winner-learning-v309-circuit-date-blocked"
WINNER_LEARNING_MIN_RACES = max(100, int(os.getenv("WINNER_LEARNING_MIN_RACES", "120")))
WINNER_LEARNING_MIN_DAYS = max(6, int(os.getenv("WINNER_LEARNING_MIN_DAYS", "8")))
WINNER_LEARNING_MIN_DATA_QUALITY = max(0.25, min(0.85, float(os.getenv("WINNER_LEARNING_MIN_DATA_QUALITY", "0.45"))))
PRERACE_FREEZE_MINUTES = max(1, min(20, int(os.getenv("PRERACE_FREEZE_MINUTES", "10"))))
_WINNER_LEARNING_CACHE = {}
_WINNER_LEARNING_LOCK = threading.Lock()


install_component(135, "_prediction_clock_state", globals())


def _learning_probability(rows:list[dict], weights:dict, power:float=1.0, shrink:float=0.0)->list[float]:
    """Market-independent winner distribution from immutable pre-race lock fields."""
    if not rows:return []
    p1=_prob_vector([float(x.get("p1Probability") or 0) for x in rows])
    win=_prob_vector([float(x.get("winEvidenceProbability") or 0) for x in rows])
    pair=_prob_vector([float(x.get("pairwiseWinRate") or .5) for x in rows])
    w1=float(weights.get("p1",.58));w2=float(weights.get("winEvidence",.24));w3=float(weights.get("pairwise",.18))
    raw=[max(1e-12,w1*p1[i]+w2*win[i]+w3*pair[i]) for i in range(len(rows))]
    pw=max(.55,min(1.65,float(power or 1.0)))
    raw=[x**pw for x in raw];sm=sum(raw) or 1.0;probs=[x/sm for x in raw]
    sh=max(0.0,min(.25,float(shrink or 0.0)));u=1.0/len(rows)
    if sh:probs=[(1-sh)*x+sh*u for x in probs]
    sm=sum(probs) or 1.0
    return [x/sm for x in probs]


def _learning_metric(races:list[dict], weights:dict, power:float=1.0, shrink:float=0.0)->dict:
    """Winner metrics from immutable pre-race probabilities only.

    Top-1 is the primary objective. Log loss, Brier and ECE are calibration guards;
    they prevent a superficially good ranker from becoming over-confident.
    """
    if not races:return {"races":0,"top1":0.0,"logLoss":None,"brier":None,"ece":None,"hits":0,"horseSamples":0}
    hits=0;ll=0.0;br=0.0;used=0;cal=[]
    for z in races:
        rows=z.get("horses") or [];winner=int(z.get("winnerNo") or 0)
        probs=_learning_probability(rows,weights,power,shrink)
        if not probs or winner<=0:continue
        try:wi=next(i for i,x in enumerate(rows) if int(x.get("horseNumber") or 0)==winner)
        except StopIteration:continue
        pred=max(range(len(probs)),key=lambda i:(probs[i],-int(rows[i].get("horseNumber") or 999)))
        hits+=1 if pred==wi else 0;ll-=math.log(max(1e-12,probs[wi]));br+=sum((p-(1.0 if i==wi else 0.0))**2 for i,p in enumerate(probs));used+=1
        cal.extend((float(p),1 if i==wi else 0) for i,p in enumerate(probs))
    ece=0.0
    if cal:
        for bi in range(10):
            lo=bi/10;hi=(bi+1)/10
            vals=[x for x in cal if x[0]>=lo and (x[0]<hi or (bi==9 and x[0]<=hi))]
            if vals:
                pm=sum(x[0] for x in vals)/len(vals);ar=sum(x[1] for x in vals)/len(vals)
                ece+=abs(pm-ar)*len(vals)/len(cal)
    return {"races":used,"hits":hits,"top1":round(hits/used,6) if used else 0.0,
            "logLoss":round(ll/used,6) if used else None,"brier":round(br/used,6) if used else None,
            "ece":round(ece,6) if cal else None,"horseSamples":len(cal)}


def _learning_races(as_of_date:str,circuit:str)->list[dict]:
    """Load only completed races with an immutable, market-independent pre-race lock."""
    if not RACEDB.path.exists():return []
    conn=sqlite3.connect(RACEDB.path,timeout=4);conn.row_factory=sqlite3.Row
    try:
        dbrows=conn.execute("SELECT race_date,payload FROM race_snapshots WHERE race_date<? AND circuit=? ORDER BY race_date,track,race_no",(as_of_date,circuit)).fetchall()
    finally:conn.close()
    out=[]
    for row in dbrows:
        try:d=json.loads(row["payload"])
        except Exception:continue
        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else None
        result=d.get("result") if isinstance(d.get("result"),dict) else None
        if not lock or not result or result.get("status")!="確定":continue
        if lock.get("marketIndependent") is False:continue
        try:quality=float(lock.get("dataQuality") or 0)
        except Exception:quality=0.0
        if quality<WINNER_LEARNING_MIN_DATA_QUALITY:continue
        fs=[x for x in (result.get("finishers") or []) if isinstance(x,dict) and int(x.get("finish") or 0)>0]
        if not fs:continue
        fs.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)));winner=int(fs[0].get("horseNumber") or 0)
        horses=[x for x in (lock.get("horses") or []) if isinstance(x,dict) and int(x.get("horseNumber") or 0)>0]
        if len(horses)<4 or winner not in {int(x.get("horseNumber") or 0) for x in horses}:continue
        # Never learn from results, odds, popularity or post-race recomputation.
        if not all("p1Probability" in x and "winEvidenceProbability" in x and "pairwiseWinRate" in x for x in horses):continue
        out.append({"date":str(row["race_date"] or ""),"winnerNo":winner,"horses":horses,"dataQuality":quality,
                    "profileId":str((lock.get("learningProfile") or {}).get("profileId") or "baseline")})
    return out


def _learning_paired_top1(races:list[dict], base_w:dict, cand_w:dict, power:float, shrink:float)->dict:
    base_only=cand_only=both=neither=0
    for z in races:
        rows=z.get("horses") or [];winner=int(z.get("winnerNo") or 0)
        bp=_learning_probability(rows,base_w,1.0,0.0);cp=_learning_probability(rows,cand_w,power,shrink)
        if not bp or not cp:continue
        b=rows[max(range(len(bp)),key=lambda i:(bp[i],-int(rows[i].get("horseNumber") or 999)))]
        c=rows[max(range(len(cp)),key=lambda i:(cp[i],-int(rows[i].get("horseNumber") or 999)))]
        bh=int(b.get("horseNumber") or 0)==winner;ch=int(c.get("horseNumber") or 0)==winner
        if bh and ch:both+=1
        elif bh:base_only+=1
        elif ch:cand_only+=1
        else:neither+=1
    return {"candidateOnly":cand_only,"baselineOnly":base_only,"both":both,"neither":neither,"netWins":cand_only-base_only}


V312_CIRCUIT_METHODS = {
    # v317: expert/AI consensus prior. Central and local stay independent.
    "中央": {
        "id": "central-v317",
        "winner": {"p1": .28, "winEvidence": .42, "pairwise": .30},
        "fragPenalty": .13,
        "stableFloor": .64,
    },
    "地方": {
        "id": "local-v317",
        "winner": {"p1": .34, "winEvidence": .38, "pairwise": .28},
        "fragPenalty": .08,
        "stableFloor": .56,
    },
}

def _v312_method(circuit:str)->dict:
    return dict(V312_CIRCUIT_METHODS.get(str(circuit or ""), V312_CIRCUIT_METHODS["地方"]))

def _v312_base_winner_weights(circuit:str)->dict:
    return dict(_v312_method(circuit).get("winner") or V312_CIRCUIT_METHODS["地方"]["winner"])

def _winner_learning_profile(detail:dict)->dict:
    """Date-blocked challenger promotion with an untouched reporting-only shadow holdout.

    Parameters are selected on TRAIN/TUNE. Promotion is decided on the later PROMOTION
    block. The final SHADOW block is reported but is deliberately not used to select or
    promote the model, so it stays useful as an honest drift/generalisation signal.
    """
    asof=str((detail or {}).get("date") or _today_iso());circuit=str((detail or {}).get("circuit") or "")
    if circuit not in {"中央","地方"}:return {"version":WINNER_LEARNING_VERSION,"active":False,"reason":"unsupported-circuit","races":0}
    key=(asof,circuit);now=time.time()
    with _WINNER_LEARNING_LOCK:
        hit=_WINNER_LEARNING_CACHE.get(key)
        if hit and now-float(hit.get("_cachedAt") or 0)<300:return dict(hit["profile"])
    races=_learning_races(asof,circuit);n=len(races);unique_days=len({x.get("date") for x in races if x.get("date")})
    base_w=_v312_base_winner_weights(circuit)
    inactive={"version":WINNER_LEARNING_VERSION,"active":False,"circuit":circuit,"asOf":asof,"races":n,"days":unique_days,
              "minRaces":WINNER_LEARNING_MIN_RACES,"minDays":WINNER_LEARNING_MIN_DAYS,"minDataQuality":WINNER_LEARNING_MIN_DATA_QUALITY,
              "weights":base_w,"power":1.0,"shrink":0.0}
    if n<WINNER_LEARNING_MIN_RACES or unique_days<WINNER_LEARNING_MIN_DAYS:
        inactive["reason"]="insufficient-locked-races-or-days"
        with _WINNER_LEARNING_LOCK:_WINNER_LEARNING_CACHE[key]={"_cachedAt":now,"profile":inactive}
        return dict(inactive)
    split=_learning_date_split(races);train=split["train"];tune=split["tune"];promotion=split["promotion"];shadow=split["shadow"]
    if min(len(train),len(tune),len(promotion))<8 or len(shadow)<4:
        inactive["reason"]="insufficient-date-blocks";inactive["split"]={k:len(split[k]) for k in ("train","tune","promotion","shadow")};return inactive
    base_train=_learning_metric(train,base_w,1,0);base_tune=_learning_metric(tune,base_w,1,0)
    candidates=[]
    # Fixed search space; no market features and no access to promotion/shadow labels.
    for p1i in range(40,76,5):
        for wei in range(10,41,5):
            pai=100-p1i-wei
            if pai<5 or pai>35:continue
            w={"p1":p1i/100.0,"winEvidence":wei/100.0,"pairwise":pai/100.0}
            for power in (.75,.90,1.00,1.10,1.25,1.40):
                for shrink in (0.0,.04,.08,.12):
                    tm=_learning_metric(train,w,power,shrink);vm=_learning_metric(tune,w,power,shrink)
                    train_drop=max(0.0,base_train["top1"]-tm["top1"])
                    score=(vm["top1"]-base_tune["top1"])*1.00+(tm["top1"]-base_train["top1"])*.18-train_drop*.20
                    score-=.055*(float(vm["logLoss"] or 9)-float(base_tune["logLoss"] or 9))
                    score-=.020*(float(vm["brier"] or 9)-float(base_tune["brier"] or 9))
                    candidates.append((score,w,power,shrink,tm,vm))
    candidates.sort(key=lambda x:(-x[0],-x[5]["top1"],float(x[5]["logLoss"] or 99),float(x[5]["brier"] or 99),-x[4]["top1"]))
    _,cw,cp,cs,ct,cv=candidates[0]
    base_promo=_learning_metric(promotion,base_w,1,0);cand_promo=_learning_metric(promotion,cw,cp,cs)
    base_shadow=_learning_metric(shadow,base_w,1,0);cand_shadow=_learning_metric(shadow,cw,cp,cs)
    base_all=_learning_metric(races,base_w,1,0);cand_all=_learning_metric(races,cw,cp,cs)
    paired=_learning_paired_top1(promotion,base_w,cw,cp,cs)
    tune_ok=(cv["top1"]>=base_tune["top1"] and float(cv["logLoss"] or 99)<=float(base_tune["logLoss"] or 99)+.020 and float(cv["brier"] or 99)<=float(base_tune["brier"] or 99)+.018)
    train_ok=(ct["top1"]>=base_train["top1"]-.03 and float(ct["logLoss"] or 99)<=float(base_train["logLoss"] or 99)+.035)
    # Winner-selector weights only promote when they create additional correct winners
    # in the later promotion block. Calibration-only changes do not rewrite the ranking model.
    promo_rank=(cand_promo["top1"]>=base_promo["top1"] and paired["netWins"]>=1)
    promotion_ok=bool(promo_rank)
    active=bool(train_ok and tune_ok and promotion_ok)
    profile={"version":WINNER_LEARNING_VERSION,"active":active,"circuit":circuit,"asOf":asof,"races":n,"days":unique_days,
             "minRaces":WINNER_LEARNING_MIN_RACES,"minDays":WINNER_LEARNING_MIN_DAYS,"minDataQuality":WINNER_LEARNING_MIN_DATA_QUALITY,
             "weights":cw if active else base_w,"power":cp if active else 1.0,"shrink":cs if active else 0.0,
             "challenger":{"weights":cw,"power":cp,"shrink":cs},
             "split":{"train":len(train),"tune":len(tune),"promotion":len(promotion),"shadow":len(shadow),"dates":split.get("dateBlocks",{})},
             "baseline":{"train":base_train,"tune":base_tune,"promotion":base_promo,"shadow":base_shadow,"all":base_all},
             "candidate":{"train":ct,"tune":cv,"promotion":cand_promo,"shadow":cand_shadow,"all":cand_all},
             "promotion":{"trainPass":train_ok,"tunePass":tune_ok,"promotionPass":promotion_ok,"paired":paired,"promoted":active,
                          "shadowUsedForSelection":False,"shadowUsedForPromotion":False},
             "reason":"promoted" if active else "challenger-not-promoted"}
    profile["profileId"]=hashlib.sha1(json.dumps({"c":circuit,"a":asof,"n":n,"d":unique_days,"w":profile["weights"],"p":profile["power"],"s":profile["shrink"]},sort_keys=True).encode()).hexdigest()[:14]
    with _WINNER_LEARNING_LOCK:_WINNER_LEARNING_CACHE[key]={"_cachedAt":now,"profile":profile}
    return dict(profile)



install_component(127, "_prediction_audit_from_lock", globals())


install_component(127, "_attach_prerace_audit", globals())


install_component(179, "_compact_display_snapshot", globals())

# ARVEXQ_EXTRACTED:install_race_stores
from arvexq.infra.race_stores import install_race_stores as _arvexq_installer
_arvexq_installer(globals())
del _arvexq_installer

RACEDB = RaceDataBank()

# --- v249 ARVEXQ Data Core -----------------------------------------------
# Data Lab-like normalized field monitor.  It does not depend on JV-Link/Data Lab;
# it orchestrates the existing JRA/NAR public-source collectors field-by-field,
# persists every usable snapshot in RaceDB, and keeps retrying only missing/stale
# fields instead of rebuilding the whole race blindly.
DATA_CORE_FIELDS = ("card","history","odds","body_weight","environment","result","payouts","analysis")
_data_core_lock=threading.Lock()
_data_core_running:set[str]=set()
_data_core_state={"running":False,"lastStart":0,"lastFinish":0,"checked":0,"refreshed":0,"error":""}

install_component(87, "_data_core_active_horses", globals())

install_component(153, "_data_core_result_due", globals())

install_component(87, "_data_core_health", globals())

install_component(200, "_data_core_health_hash", globals())

install_component(87, "_data_core_store_health", globals())

install_component(200, "_data_core_record_run", globals())

install_component(142, "_data_core_snapshot", globals())

install_component(38, "_data_core_refresh_race", globals())

install_component(151, "_data_core_day_rows", globals())

install_component(151, "_data_core_day_status", globals())

install_component(152, "_data_core_cycle", globals())

install_component(152, "_data_core_loop", globals())

install_component(152, "_start_data_core_collector", globals())

install_component(162, "data_core_status", globals())

install_component(151, "data_core_refresh", globals())

install_component(151, "data_core_refresh_day", globals())

_full_history_lock=threading.Lock()
_full_history_running:set[str]=set()

install_component(57, "_schedule_full_history_harvest", globals())

PREPARED_STORE = PreparedRaceStore()
_prewarm_lock = threading.Lock()
_prewarm_running: set[str] = set()
_prewarm_state: dict[str, dict] = {}


def _pc_clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def _pc_race_field(rr: dict) -> int:
    return max(4, int(rr.get("fieldSize") or 12))


def _pc_finish_quality(rr: dict) -> float:
    fin=int(rr.get("finish") or 0); fs=_pc_race_field(rr)
    if fin <= 0:return .45
    return _pc_clamp(1-(fin-1)/max(3,fs-1))


def _pc_list_quality(rows: list[dict], target_dist: int) -> float:
    if not rows:return .5
    num=den=0.0
    for i,rr in enumerate(rows):
        w=.82**i
        q=_pc_finish_quality(rr)
        ti=_pc_time_index(rr,target_dist)
        q=q*.72+(_pc_clamp(ti/18) if ti else .5)*.28
        num+=q*w;den+=w
    return num/den if den else .5


def _pc_style_metrics(horse: dict, race: dict) -> dict:
    rs=list(horse.get("recentRaces") or [])
    c=[0.0,0.0,0.0,0.0];den=early_den=early3=moved3=tempo_num=tempo_den=0.0;samples=0
    target=int(race.get("distance") or 0)
    for i,rr in enumerate(rs):
        pos_list=list(rr.get("cornerPositions") or [])
        try:pos=int(pos_list[0]) if pos_list else 0
        except Exception:pos=0
        if pos <= 0:continue
        fs=_pc_race_field(rr); norm=(pos-1)/max(1,fs-1)
        delta=abs(int(rr.get("distance") or 0)-target)
        rel=1.22 if delta<=100 else (1.08 if delta<=300 else (.74 if delta>=700 else 1.0))
        if str(rr.get("track") or "")==str(race.get("track") or ""):rel*=1.10
        if str(rr.get("condition") or "") not in ("","不明") and str(rr.get("condition") or "")==str(race.get("condition") or ""):rel*=1.05
        w=(.82**i)*rel;den+=w;early_den+=w;samples+=1
        if pos==1:c[0]+=w
        elif pos<=3 or norm<=.22:c[1]+=w
        elif norm<=.62:c[2]+=w
        else:c[3]+=w
        if pos<=3:early3+=w
        later=[]
        for z in pos_list[1:]:
            try:
                z=int(z)
                if z>0:later.append(z)
            except Exception:pass
        if pos>3 and later and min(later)<=3:moved3+=w
        ten=_pc_clamp(1-(pos-1)/max(3,fs-1));tempo_num+=ten*w;tempo_den+=w
    if not den:
        return {"front":0,"stalk":0,"mid":0,"close":0,"early3":0,"moved3":0,"ten":.5,"samples":0,"stylePoint":None,"pastStyle":"履歴なし"}
    front,stalk,mid,close=[z/den for z in c]
    point=front+2*stalk+3*mid+4*close
    name="逃げ" if point<1.65 else ("先行" if point<2.35 else ("差し" if point<3.15 else "追込"))
    return {"front":front,"stalk":stalk,"mid":mid,"close":close,"early3":early3/early_den if early_den else 0,"moved3":moved3/early_den if early_den else 0,"ten":tempo_num/tempo_den if tempo_den else .5,"samples":samples,"stylePoint":round(point,4),"pastStyle":name}


def _pc_sectional_score(horse: dict, race: dict) -> tuple[float | None, int]:
    """Closing-section evidence from historical 3F times, normalized by each run's own average speed.

    This deliberately uses only past-race data. It does not infer missing sectionals and
    never reads the current race result/market. The ratio makes the signal portable across
    distances/tracks better than comparing raw 3F seconds directly.
    """
    rows=list(horse.get("allPastRuns") or horse.get("recentRaces") or [])
    target=int(race.get("distance") or 0); num=den=0.0; used=0
    for i,rr in enumerate(rows[:8]):
        try:
            ag=float(rr.get("agari3f") or rr.get("agari") or 0)
            sec=float(rr.get("timeSeconds") or 0)
            dist=int(rr.get("distance") or 0)
        except Exception:
            continue
        if not (27.0 <= ag <= 50.0) or sec <= 0 or dist < 600:
            continue
        avg_speed=dist/sec
        close_speed=600.0/ag
        if avg_speed <= 0:continue
        ratio=close_speed/avg_speed
        # Around 1.00 is an even finish; 1.15-1.30 is a strong closing section.
        q=_pc_clamp((ratio-.96)/.36)
        try:rank=int(rr.get("agariRank") or rr.get("agari_rank") or 0)
        except Exception:rank=0
        if rank>0:
            fs=_pc_race_field(rr)
            rq=_pc_clamp(1-(rank-1)/max(3,fs-1))
            q=q*.82+rq*.18
        delta=abs(dist-target) if target else 0
        rel=1.16 if delta<=100 else (1.06 if delta<=300 else (.78 if delta>=700 else .94))
        if str(rr.get("track") or "")==str(race.get("track") or ""):rel*=1.06
        w=(.84**i)*rel
        num+=q*w;den+=w;used+=1
    return ((num/den) if den else None),used


def _pc_fit_metrics(horse: dict, race: dict) -> dict:
    rs=list(horse.get("recentRaces") or []); target=int(race.get("distance") or 0); target_season=_pc_season(str(race.get("date") or ""))
    groups={"track":[],"distance":[],"condition":[],"weather":[],"season":[],"level":[]}
    for rr in rs:
        dist=int(rr.get("distance") or 0);delta=abs(dist-target)
        if str(rr.get("track") or "")==str(race.get("track") or ""):groups["track"].append(rr)
        if delta<=100 or (target>=1800 and delta<=200):groups["distance"].append(rr)
        if str(rr.get("condition") or "") not in ("","不明") and str(rr.get("condition") or "")==str(race.get("condition") or ""):groups["condition"].append(rr)
        if str(rr.get("weather") or "") not in ("","不明") and str(rr.get("weather") or "")==str(race.get("weather") or ""):groups["weather"].append(rr)
        if _pc_season(str(rr.get("date") or ""))==target_season:groups["season"].append(rr)
        rp=int(rr.get("racePrize1") or 0);tp=int(race.get("racePrize1") or 0)
        if tp>0 and rp>=tp*.8:groups["level"].append(rr)
    out={k:_pc_list_quality(v,target) for k,v in groups.items()}
    out["counts"]={k:len(v) for k,v in groups.items()}
    return out


def _is_jump_run(run: dict) -> bool:
    return bool(re.search(r"障害|ジャンプ|J[・･.]?G|\bJS\b",str(run.get("surface") or "")+str(run.get("title") or ""),re.I))


def _evaluation_number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


# ARVEXQ_EXTRACTED:install_evaluation_core
from arvexq.domain.legacy_evaluation import install_evaluation_core as _arvexq_installer
_arvexq_installer(globals())
del _arvexq_installer


install_component(129, "_ensure_race_volatility", globals())



install_component(67, "_restore_saved_odds", globals())


install_component(110, "_precompute_detail_metrics", globals())


install_component(149, "_prepared_ttl", globals())


install_component(86, "_snapshot_final", globals())


install_component(149, "_prepared_get_fresh", globals())


from arvexq.ingest.result_status.confirmed import official_confirmed

install_component(153, "_result_has_podium", globals())


install_component(153, "_refresh_result_fast", globals())


install_component(159, "_prepare_race_snapshot", globals())


install_component(151, "_prewarm_sort_key", globals())


install_component(151, "_schedule_prewarm", globals())


install_component(159, "_ensure_detail_background_jobs", globals())


install_component(159, "_schedule_detail_background_jobs", globals())


_racedb_refresh_lock=threading.Lock()
_racedb_refresh_running:set[str]=set()

install_component(110, "_fast_local_race_detail", globals())


install_component(110, "_build_fast_diagnosis_snapshot", globals())


install_component(110, "_store_fast_snapshot", globals())



_fast_card_lock=threading.Lock()
_fast_card_running:set[str]=set()
_fast_card_pending:set[str]=set()
_fast_card_queue=[]
_fast_card_cv=threading.Condition()
_fast_card_workers_started=False

install_component(159, "_ensure_fast_card_workers", globals())

install_component(159, "_queue_fast_card", globals())

install_component(159, "_fast_card_worker", globals())

from arvexq.ingest.nar_official_card import parse_card_html as _parse_nar_official_card

install_component(21, "_parse_nar_official_card_html", globals())

install_component(21, "_nar_official_card_rows_fast", globals())


install_component(38, "_merge_current_card_fields", globals())


install_component(153, "_nar_result_should_be_available", globals())


from arvexq.ingest.nar_result import parse_result_html as _parse_nar_result_html


install_component(21, "_nar_official_result_fast", globals())


install_component(25, "_netkeiba_card_rows_fast", globals())


install_component(38, "_merge_card_rows_preserve", globals())


install_component(57, "_netkeiba_past_rows_fast", globals())


install_component(57, "_merge_fast_history", globals())


install_component(38, "_hydrate_fast_card_now", globals())

install_component(38, "_schedule_fast_card_refresh", globals())


install_component(38, "_schedule_racedb_snapshot_refresh", globals())

install_component(142, "_racedb_get_fast", globals())

_detail_cache_lock=threading.Lock()
_detail_cache:dict[str,tuple[float,dict]]={}

_race_list_cache_lock = threading.Lock()
_race_list_cache: dict[str, tuple[float, list[dict]]] = {}


install_component(151, "_local_starter_bundle", globals())


_volatility_pack_lock=threading.Lock()
_volatility_pack_cache:dict[str,tuple[float,list[dict]]]={}

install_component(129, "_local_volatility_map", globals())


install_component(129, "_attach_local_volatility_to_summaries", globals())


install_component(129, "_compute_local_volatility_for_race", globals())


install_component(170, "volatility_pack", globals())


install_component(163, "races", globals())



install_component(169, "environment_pack", globals())


install_component(163, "track_pack", globals())




_site_bootstrap_lock=threading.Lock()
_site_bootstrap_build_lock=threading.Lock()
_site_bootstrap_cache:dict[str,tuple[float,dict]]={}
_site_force_cache:dict[str,tuple[float,dict]]={}
_site_bootstrap_state:dict[str,dict]={}

install_component(141, "DayBundleStore", globals())

DAY_BUNDLES=DayBundleStore(DAY_BUNDLE_DB_PATH)

install_component(141, "_bootstrap_rows_local", globals())

install_component(141, "_bootstrap_sources_running", globals())

install_component(141, "_bootstrap_display_ready", globals())

install_component(141, "_bootstrap_analysis_ready", globals())

# Compatibility for older internal callers: "ready" now means display-ready.
install_component(141, "_bootstrap_detail_ready", globals())

install_component(141, "_bootstrap_detail_local", globals())

install_component(141, "_assemble_day_bundle", globals())

install_component(141, "_refresh_day_bundle", globals())

install_component(141, "_schedule_day_bundle_refresh", globals())

install_component(141, "_site_bootstrap_payload", globals())

install_component(141, "_force_day_live_snapshot", globals())

install_component(141, "site_bootstrap", globals())

install_component(141, "_site_bootstrap_warm_loop", globals())

install_component(141, "_start_site_bootstrap_warmer", globals())


install_component(162, "site_bootstrap_status", globals())


install_component(166, "past_pack", globals())



install_component(159, "prepare_race", globals())


install_component(151, "prewarm_track", globals())


install_component(162, "local_refresh_status", globals())

install_component(162, "central_refresh_status", globals())

install_component(164, "race_detail", globals())



install_component(170, "diagnosis_refresh", globals())


install_component(171, "snapshot_version", globals())


install_component(165, "horse_snapshot", globals())


install_component(162, "prewarm_status", globals())


install_component(167, "collect_race_info", globals())



install_component(168, "payout_refresh", globals())

install_component(66, "_merge_live_market_rows", globals())

install_component(167, "odds_refresh", globals())


_auto_odds_lock=threading.Lock()
_auto_odds_last:dict[str,float]={}
_auto_odds_state={"running":False,"lastStart":0,"lastFinish":0,"checked":0,"updated":0,"error":""}

install_component(155, "_auto_odds_targets", globals())

install_component(155, "_auto_odds_cycle", globals())

install_component(155, "_auto_odds_loop", globals())

install_component(155, "_start_auto_odds_collector", globals())

install_component(162, "odds_auto_status", globals())


install_component(110, "racedb_save_analysis", globals())

install_component(170, "racedb_get_analysis", globals())

install_component(197, "model_audit", globals())


install_component(197, "model_learning", globals())


install_component(171, "racedb_status", globals())

install_component(164, "racedb_race", globals())

_racedb_daemon_started=False
_racedb_daemon_lock=threading.Lock()

install_component(152, "_racedb_live_cycle", globals())

install_component(152, "_start_racedb_daemon", globals())

install_component(162, "enrichment_status", globals())

install_component(162, "enrichment_schema", globals())

install_component(200, "build_info", globals())


install_component(176, "home", globals())





from arvexq.ui.icon_assets import load_icons as _load_arvexq_icons
ARVEXQ_ICONS = _load_arvexq_icons()



install_component(193, "arvexq_icon", globals())


ARVEXQ_TOUCH_ICON_180 = read_binary_asset("arvexq-touch-icon-180.bin")

CINEMATIC_HERO_WEBP = read_binary_asset("cinematic-hero-webp.webp")
CINEMATIC_DETAIL_WEBP = read_binary_asset("cinematic-detail-webp.webp")
install_component(193, "arvexq_touch_icon", globals())


install_component(195, "cinematic_detail_photo", globals())

install_component(195, "cinematic_hero", globals())


install_component(195, "arvexq_logo", globals())

install_component(195, "hero_horse", globals())

install_component(195, "pace_preview", globals())

install_component(200, "version_json", globals())

install_component(195, "styles", globals())

install_component(198, "appjs", globals())

install_component(193, "manifest", globals())

install_component(193, "service_worker", globals())


# Start the v86 RaceDB updater after module initialization.
# ARVEXQ_DATABANK_REGISTRY
register_legacy_sources(globals())

_start_racedb_daemon()




# v158 upset targeting / race selection



























































# v239: simplified horse detail and persistent live iframe












