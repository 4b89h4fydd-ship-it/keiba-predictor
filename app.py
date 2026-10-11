from arvexq.ingest.supplemental.state import _enrich_jobs_lock
from arvexq.ingest.supplemental.state import _enrich_jobs
from arvexq.ingest.supplemental.state import _enrich_data_lock
from arvexq.ingest.supplemental.state import _enrich_data
from arvexq.ingest.history.jobs import _full_history_lock
from arvexq.ingest.history.jobs import _full_history_running
import arvexq.ingest.snapshots.local as _acq_snapshots_local
import arvexq.ingest.snapshots.hydration as _acq_snapshots_hydration
import arvexq.ingest.history.harvest as _acq_history_harvest
import arvexq.ingest.supplemental.enrichment as _acq_supplemental_enrichment
import arvexq.ingest.snapshots.results as _acq_snapshots_results
from arvexq.ingest.central.jra.state import JRA_BAD_TITLE_RE
from arvexq.ingest.central.jra.state import JRA_CNAME_RE
from arvexq.ingest.central.jra.state import JRA_HORSE_CNAME_RE
from arvexq.ingest.central.jra.state import JRA_MEETING_DAY_RE
from arvexq.ingest.central.jra.state import JRA_PROGRAM_TRACK_RE
from arvexq.ingest.central.jra.state import JRA_RESULT_CNAME_RE
from arvexq.ingest.central.jra.state import JRA_TRACK_CODES
from arvexq.ingest.central.jra.state import JRA_TRACK_CODE_BY_NAME
from arvexq.ingest.central.jra.state import _jra_cache_lock
from arvexq.ingest.central.jra.state import _jra_cname_lookup
from arvexq.ingest.central.jra.state import _jra_cname_lookup_lock
from arvexq.ingest.central.jra.state import _jra_program_cache
from arvexq.ingest.central.jra.state import _jra_program_cache_lock
from arvexq.ingest.central.jra.state import _jra_text_cache
from arvexq.ingest.environment.state import _environment_http_cache
from arvexq.ingest.environment.state import _environment_http_lock
from arvexq.ingest.local.state import NAR_BABA_CODES
from arvexq.ingest.local.state import NAR_NETKEIBA_CODES
from arvexq.ingest.local.state import _nar_odds_cache
from arvexq.ingest.local.state import _nar_odds_cache_lock
from arvexq.ingest.local.state import _nar_sync_io_lock
from arvexq.ingest.history.jobs import _race_history_jobs
from arvexq.ingest.history.jobs import _race_history_lock
from arvexq.ingest.netkeiba.state import NETKEIBA_TRACK_CODES
from arvexq.ingest.netkeiba.state import _netkeiba_cache
from arvexq.ingest.netkeiba.state import _netkeiba_cache_lock
from arvexq.ingest.supplemental.state import _smart_cache
from arvexq.ingest.supplemental.state import _smart_cache_lock
import arvexq.ingest.central.jra.transport as _acq_central_jra_transport
import arvexq.ingest.central.jra.identifiers as _acq_central_jra_identifiers
import arvexq.ingest.central.jra.program as _acq_central_jra_program
import arvexq.ingest.central.jra.history as _acq_central_jra_history
import arvexq.ingest.central.jra.racecards as _acq_central_jra_racecards
import arvexq.ingest.central.jra.calendar as _acq_central_jra_calendar
import arvexq.ingest.central.jra.results as _acq_central_jra_results
import arvexq.ingest.central.feeds as _acq_central_feeds
import arvexq.ingest.central.history as _acq_central_history
import arvexq.ingest.central.racecards as _acq_central_racecards
import arvexq.ingest.local.archive as _acq_local_archive
import arvexq.ingest.local.history as _acq_local_history
import arvexq.ingest.local.racecards as _acq_local_racecards
import arvexq.ingest.local.odds as _acq_local_odds
import arvexq.ingest.local.results as _acq_local_results
import arvexq.ingest.netkeiba.transport as _acq_netkeiba_transport
import arvexq.ingest.netkeiba.history as _acq_netkeiba_history
import arvexq.ingest.netkeiba.program as _acq_netkeiba_program
import arvexq.ingest.netkeiba.rows as _acq_netkeiba_rows
import arvexq.ingest.netkeiba.racecards as _acq_netkeiba_racecards
import arvexq.ingest.netkeiba.odds as _acq_netkeiba_odds
import arvexq.ingest.netkeiba.results as _acq_netkeiba_results
import arvexq.ingest.supplemental.feeds as _acq_supplemental_feeds
import arvexq.ingest.environment.parsers as _acq_environment_parsers
import arvexq.ingest.environment.transport as _acq_environment_transport
import arvexq.ingest.environment.providers as _acq_environment_providers
import arvexq.ingest.merge.current as _acq_merge_current

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

app = FastAPI(title="ARVEXQ", version="14.25-v329-racecard-stable")
app.add_middleware(GZipMiddleware, minimum_size=900, compresslevel=5)

PREDICTION_ENGINE_VERSION = "arvexq-edge-2026.10-v53-consensus-rebuild"
ARVEXQ_DATA_CORE_VERSION = "arvexq-data-core-v300-final"
AI_EVALUATION_VERSION = "evidence-v317-consensus-rebuild"
VOLATILITY_ENGINE_VERSION = "arvexq-volatility-v1"

from arvexq.prediction.legacy_model_tables import (
    V207_WINNER_MODEL_VERSION,
    V207_VALIDATED_CIRCUITS,
    V207_WINNER_WEIGHTS,
    V207_BACKTEST_AUDIT,
    V212_P2_MODEL_VERSION,
    V212_P2_MODEL_INTERCEPT,
    V212_P2_MODEL_COEFFICIENTS,
    V212_ROLE_AUDIT,
    V213_ROLE_MODEL_VERSION,
    V213_VALIDATED_CIRCUITS,
    V213_FEATURES,
    V213_MEAN,
    V213_SCALE,
    V213_P1_COEF,
    V213_P2_COEF,
    V213_P3_COEF,
    V213_BLEND,
    V213_BACKTEST_AUDIT,
    V215_PRO_MODEL_VERSION,
    V215_P1_BLEND,
    V215_FEATURES,
    V215_MEAN,
    V215_SCALE,
    V215_P1_COEF,
    V215_SPEED_BASE_EXACT,
    V215_SPEED_BASE_TRACK_DISTANCE,
    V215_SPEED_BASE_DISTANCE_GOING,
    V215_SPEED_GLOBAL,
    V215_DRAW_STATS,
    V215_TRACK_DRAW_STATS,
    V215_RESEARCH_AUDIT,
)


@app.middleware("http")
async def _arvexq_timing(request: Request, call_next):
    started=time.perf_counter()
    response=await call_next(request)
    try:response.headers["X-ARVEXQ-ms"]=f"{(time.perf_counter()-started)*1000:.1f}"
    except Exception:pass
    return response

INDEX = read_asset("index.html")

CSS = read_asset("styles.css")


JS = read_asset("app.js")

MANIFEST = r'''{
  "name":"ARVEXQ",
  "short_name":"ARVEXQ",
  "description":"ARVEXQ — PACE · POSITION · VALUE",
  "start_url":"/?pwa=1&v=329",
  "id":"/arvexq-v175-install",
  "icons":[{"src":"/arvexq-icon-v175-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"/arvexq-icon-v175-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}],
  "scope":"/",
  "display":"standalone",
  "background_color":"#041126",
  "theme_color":"#0b1220",
  "lang":"ja"
}'''
SW = r'''const RESET_TAG="arvexq-reset-v329";
self.addEventListener("install",function(event){event.waitUntil(self.skipWaiting())});
self.addEventListener("activate",function(event){
  event.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.map(function(k){return caches.delete(k)}));
  }).then(function(){return self.clients.claim()}));
});
// v319 reset worker does not intercept requests. Network is authoritative after deployment.
'''

HERO_HORSE_WEBP = base64.b64decode('UklGRj4TAABXRUJQVlA4IDITAADwWgCdASoiAcgAPlUokEajoqGoJNN5yQAKiWNuvTN5rijgeFDKpI+O3yJhZjLWvD+58pvk7JAteekfzBugR5j/OA9R3lY9ctvT/7pTLnNT2puDsw3TZ6AHjCaM/rb2DR0vuEBqcidU3VEnR513uUEYs/p5V2+UUrdCK648Wo44eworQVyKmaVSlplKHAT5Tzbd0VcAzHwj4Q6HqVV255ewOERF6o77QvfVkYXfxZr49ackkH92cNeYATc3Y3Jj3BYN+3Av3LXjSkiHSCZm5Yd2x8W5IkLKC393I1OfWkmI7fA0lcpT/7lG/U7X5Vw8JsxZUhFVsCV7mc1x+TOgiWCdrmDd430g69/uizYPx2eUWydN85FyXkZLHEDrCMjeJnc7iB+rXf4iDREMc3Brjrgn3qZQ97VPB2OHzJG7ecbRf3/e1Dyx5XX2CFQ1KXANNiCtmsOV5XGHek0yBP4npxiYmSvHifpggMz1PUB6AcjUWTq3Qb0MpP4bst5K0bL+ldCJdEkwbHcV2C8PPS+vidJdvaxfJz6E73QAJZRiFe37TaINkDnEWwPa5qXHqA/p/42esik/qgreA9q6+TZR9ClKpNF0IpX5eWyu+KmP+uKQ75dqPC9gzwy8jz65jfzTgBugFikZORudP9jlHTf/9K9mlh/54NeYAcJv6sObaqRWTvHcuzeIQK5PBYv8OpecUQFvLV6oTAWyd0EuNgh4PBQ8AYvV4KzwV2CHmiuuidlDqdEBy5e7YEG0cb8phGpZEwuWqqX7bD8GgTX5lGQ/hoVtaTyDHsNb/rhG9rK1mza5fFUmeanQIB6BUphb0MnNeEh2bKyc0h9dptxcFQqK1wSDlZfjSgOJxCvtWrpiX9FHCtFZ77fD7FIQ4q4HYGpQQin0tL3LsfpXe7YmjGcWQ3gbzi45kDDJBoIhg42G4oVtVQnxP0kT/FtLQAot5cuXvDtLMBGTQ8rFN7KK7lucL5SYAP76bVSKz//p+f/5X7/9Pz8Xb/+P5/oX/Hqwhx3JXu8E2HsVQRFAor+ciAi917lC+B+/Tl73717Kl4pAHn5pB79jSNgXcTvnydzlCXw9P9mDL2Yl2pq3EKW2PZnpkev1QwEmLBA7E1ohtKLeV8FvFoTDE7RSBTsPTzYPRXCKdvhbO7U+QtFQyNIw00w3IMXXTCuK+FO8o1Yi1WnOu/O1vv4GBdmeBC2koAYJnUmKMc/yNQPLPGob06POKADrrRE6UJDYbicyx4vK1AtQD3E1K5hD+17gTlhLwFrS4zkOxVKPNkzWzAl6Sig1QShaLr3y9TQqoDEjSV/AhDOUCqVxVg2hQTuZiqJtSIpzuObJzhP3rPa0wAFQ5hYdEcVxkXmC8Mtipr/r+VgGo1ADLXDpcotNk8D36E2D/pW26MrMKoOfv6EqImhwiqzCxUZ06fAtBP3FcOlg6mL4DMUi5l71Ehyn+/Iqe+pR44APIpIwf8Q9SvTeOBN1XMAqQBwM76yG+bJhyrdAwSQWt0Ro8NUSTDTaoS959mYJQ1okOHa1E3c1e7ZorojP+qbX91UudQuxpwmkA1myo0UW/EoOu4R3zfueP1EUAuoeDuLX232vO+no+FKBwndWgewin43X2HdF0AmchNp21G7wnm2ii4jIFdtdrBn3D3nwxgCjjulqU8az8x0WS04qVh8VpygUihS3PJg67s9a8S4H0CkHrl590hXqyW6iw1hlbqlr3S5GEPJpKxFkMp5gE6SQrb5WDf5ekHC512ClH1Sk8fbNirNGgZBs8AzbcL+ExTK/NruqNjoDPttMiurJm2fL9S00elMiRks0ZvSqstTip7q43cnUvtAxVeVXF655KLb2egbsN6EDR9IQ5K0AvXEfhEnVXk9t8Dby52U7alij13MJyeGflPO5pqPd/NPI9Dfa8eAC9KKxFcGF4mDcJF0fGfm1FCLQgu0ffQvp0EaGMre+EJ+1Dcul2Au5EfIkdwou0ZxlT33inviNt0qmWA8irpXB6mgGLbkaKkuPq9r4lGaYO7UWzYiMH3HKHHBs/Mg7nUB2+qhxPD7qEs0wx2JfIryGhP7nTVA2n9xqkfYOGwOLSWG6apUV+dE8ZGBRrm4mH07d2N0rfqyO1dZOhJOaj3lzljNnZ2Fjrsm0aYdttW2L70HrwrfNv9+SpLeWyRDfchWskaqyWV5olRkAVbkXWoS6wOlvEe3TMHeIX8Ip1t7kRRKyuuPxkHTIjy99h/OuNrvjf4pn1cEqUISa8QdLWGkl0xM5jKD0vRA3LXkQ8SEsTrQh/gt7wB5Mg2ZTD5ECXuHKBH5jovKfKTbVrfhvoc4lIoJOVMpp5IuouTV2B8od84QukLHlo7IqqrWT1NOWK2jVdrCYp5BiH7+qW07W5+5933huSluEGhSMIn90znFmiFiPM7Td5d6EC2WwGDtEhAuxpN1HjE6FOgamybQM0T0Tn8XdTv/vMBJxVCtFinAhMnXLMzlz38VvW9Ba2GPrz7rE74kIaqdPvMBFsz06qNlQhcNr7Ak4n0zmoH7F5fSrO8GNaWh79o3rewOkfPPMnUpWcgsucArAdLFCuJCfkscJW7t/8Ms7sv7yEW7a70DjE8dG7oMYA2XrpPwiRo4OoIVDhdm97YlyxhQI8BSLu37XVfs76B/eZbyj2Wu/IawmSGd355R3GZw4Fe4vey5xi5vRb07eOKuE8FfDqTF7U/jb/uEy4XDTi9IZVevHwF0st7SZHvC+bletHFEzz2OljMrNenW0+3hvzi9htUCGgHErBSTjc0NFi/uWr0T9eilrd0uXmBjseUnywQ+bvLisMN3A+zcWoJf8A595qYNf10PKRn5RKTElsFSipuiiOwIzi0NuAQa4Tq23J34NBdgS2WwzbZJoRyE8YjuS8bimXLZ89Aq29Xf9wydkHljaVzPg8dCBBq6raxSSwSTmamX2TAQnZBzax0uBD7OHwP33XUYLYuUi23/XC+e/DVAEGRWxqvMe8PW3XfmhJx8XGqtlUuUz+GNpHk2qdUaKtXg4ST4vg8fe7SWDyOPb7vTYw9auu4KaYi86qr0uMM233UIu+tMG3/11Gfh+gfmH5pkU7S16MLgvTlqwbhQNVVOLNXBwpcQ+lg9AOONGw78P0Y22pxNHW/yEwH654y6L8kpbQtbhrQOsdj6zPlvxbcJkX1uDbC3x8o4zX3EV5tfcQB2FM8LyJr13JRAWC4Z0qkGGUG/lg3I/n8pQP/MX+MaCoxe97X/gn+94aLhE1E/MtKV4hSAfs6Ly1PfdbmUEnxkH9bYPUgm2+T0+SGkJDeFnY/2zq/AaalrkguUtdC8BRS1h8B2CSSHn0xWwingeOOax+O8VUQMIfpS8/CC/vTB/ZJvx+94IOCD243SJ8ThtCOin+L5eFIIFhrZ1R9Vpx5FqC04k9uh3cNnm91lzeFod7KMQMWjvJEELw5XoIXqjhp9TUjaOjIF6Z5pHxXcrxk0Mo7reBBm4vHnqBbJPmyhP2EP7+MuPHQUugDjoQBNayZj5c8mORwGJheWvZUllahCxPLnohk4PVHi+6oSWzIzc45mLBrYtLaaYd6HUUJxbC9xHklzuLI7lfoEXphMcgz4lurlqkdEITIkm2bfMJjqwPaSe/sXfNuYe9OqcK2j2ZjBl9AMdA6TqaGwJBGSLQY2/kMljbZw42EvcwBbkAwWU4Pm2RDZLXyQeikOhfR1EeJIQLMYBoiiI9K9yw3CFwJoLEj+eeToS3sEtkVnd6j/iRJUUNppXawCIj6O3GASrBSKKzhqdoObJeUxIz3aC6EXvmNDGgZ8TeK+kDeSeKnO9kt/QwaGWB69F/OBX8HNQ5ue3mB+JWBZp5xAEHfZBkC0Xlf773iqZJ9EBu6Q6RP85Y9MOqP0tsEty78H3/wShF8FUkMkaD8dVZiQ4tk4qnfUqNdL9mzRaZ+HI58xS4/xZ0F/MrBPjYPAnlMvsLLJqsEwD+xp6exaWJ0mm1GqQsATwwY1xlJOjLZdctSS8symGsvS63gtzDYzAdUSq7Eus9RcqjPL967WEetzxx4QrlB11OP208VSbGDx+wmcVNPrkSFWils9gKTsjF5DelVuCpOULu8fSgYvGEspjm+h+5IcmxOmhCvrgLCf3KOPrqnoC4INL25MSsgICTaGJ4vjFEGvZBxwsJE4sZm7/BC0sFGvB8wIUFU8NiIWMBXKK5eLbB3MocamArf9gLxmv3wqtjo6qzSUNnpPlmSUnAGGPzi6PDfic5LgUwFd08pM5Q9Wnxkzn65hA9vsNcqew4ppO3b70mkU2A5FdAVHswNymld5XGDhaPZos38mTKxQI5xAe9P2P3BvNCIsLwm/NibH3Nl/evCD2y7qcKPDlZd5H38DwlBLKixg9uwM5+/bfpOdhU48QQ0GEpsPg08PdLcAzmkxDg1Z8BPtWaudSNX++S32Z9pGEWXtwf8XavefW7UXW115KhRgp0NePXmFRx9LRMrOp7Djdlh1IPAmD7gCp+S4L9PMiuLnkZWUM2mR2xfLL9w3ceIeDnOq4dpg3vi5WbX6s2JzWCYPgNsU4Y5bobqlU5S4JDO4G52rEW+0n9iGfMpr5P6xzmBHeCBDgODXktthsBfmHUeg+UDkXi1NHjoQ6uGmiZudtj18ovOCCo+w6outoSr/w13LB3KbJaXamG4K3s29mRt6fI6jKOMLw5jVeRwLTi+o0bQbRytx94EvCRuKsjfMwh1r7iZItVgxCYcG65Xpqze9QKA/QfsfIMy/g+c9wLEK5H+jht6R4Zt2WLvBgC6tWWws7BZg7Iyi58hCTdS1rDvVmFeF59M4FR7hKrar1ldVKxz7wDqOOn7HNluJK95pyUaZA6mcefB7qRumTCQ+U59nAe5KC5GoHMxr75RRLxnEY3hCSIIH/t7CN+Ku5g4PoZs3kL0cXOM2UDWB1nxgu1HMICoY7KcV4jlMucPrKkeJ7f7yFDTEUQgQMU0oYPDSfDe9pyNvGjhu1L/1lAWovy9t4kPczkrrq1lTp54wjh0IDPHxNGuM/p4UyRSDYGme64p6XaGTlawkhnXD8QWPJ339qROKFk9OgZNwiTzhRjNrmihbf/lIITxRqHbOkcH9R7JBbeXct0BV1S10FOYMbkrFGGMAxWPN70FwL9RFc0BUOV9KHL16VQPoRXHvXnA84+jmxMuLuaeiKor+x+DmAGrs1xrWy/PbCClsHfSNpGexTPbCXfC1q4GrBetyWU+3pxGjnxhVsDszorH2XeIMgILUfqNz9DE5aYFEHyBYlVhK/NgldJZTZg4Ds/eREMe4Dz/BBmndIMphoeMtdFnG+Ahmedl7y/tBpS/ngyYmHIZwxC6YOgQRj6VZi37Oad/uvxXzmw5z9HN3SU7XyYS7/MfQFPVtEe/ZBunNF2gDKZ7NZsuUT1U5FwJfvcRAWYwbknkXOlOeTSDsUdah/15X/wnvJ+J286d5W/0A6v2udLOUF5xG2Ecd7QxT4aXjLau2JclUUD2WE0EFKp8Oz0LmrFZcghurwYukJ7DQOPsRWYyyhRg3rlMzjONXJ9YeYZt9OIG3w8dTEJCjIg7XP5rVhSv8seg68KrLPHc/NAUXVyoEmG9NbAEWg3HUZGR7Kjm3fzMeGsNRckLxpAXnvMKvz3rhhIgD66tw4IBaLvHez4bQFp6YMBLJNW1LOOldUl8c9vrSOD9biLu0poZ52ROyhbOvPEczqn5A5XTNtNPrtopsrmnOfASOQ344jyj7V/xauVU/oZ1P+VQ9ECArWF6Uo/poabCy0GM+r492L6wy++kAjt0zpe/8wGHzBdXJAwE3Kg2srIS3g37LQDV885KxWiVxqQ9iuEN37T8P9d9+UqVnHXwFcwbRlKm8P2igfOuf2AQgOQ/HgYUUQLzcQObXXjZlPJivL+WCbiMjs/1Mp00/No4sS3h0iMKsZGpSd327pBDRGGBZSqVEH0ZNI/ov9O8htz8nB8A8iBTnG9OgvINYUdhfEMrS3IS0roKKAeKBrnBIQsTD46nxC1AhaNc0eer3SN2dDuPUFwhcKYacLnKP0+lEVMtgdXfke80WS5JNJJPP+4ei9ESoO9ZANzmLMnDQzjffZlw8XQuE4mwCVgN5YC/TXi47A3zXUDe7JHG21sEJhDY7KxrDkemvxS24iYIJkGoLCaWzZEDLpjYWO8YgAPIFD/YcBjChBXhBaX3Zqeg1t279mzimycJABhDZnTFGqND32dPPATutlkI7FokIoi1xxgZu37myNVNpQCdZtuVW7B9Q907Vlf6dyomGvjiUVSQD5GrVmPiDsXx5clYO6Rq73XPR8YrWtCZ1V7tSIzh2SfINhna4TtvddaRgCInHhPoTlqV4/o/CDhfzQGFz7ObsW+a9VXgwGdAi3GtJ2vIXRRKAthKg1Qi2s0t0+TqRwFvyhEHSwdtmz+gYRMdBzd82+7DOyOG8WEhCsgjFIJmuK47dR2BK1+anqdwEkqg5wViLXAgPQlkHdsxwQNjx8DeXDNsXNaSoFmxV5h/QPkOIl78+eDhjYC7+BuuSIsakFMGj/qikcJxSYshH9cFSnAAA=')
ARVEXQ_LOGO_WEBP = read_binary_asset("arvexq-logo-webp.webp")
PACE_PREVIEW_WEBP = read_binary_asset("pace-preview-webp.webp")

# --- NAR official live data connector ---------------------------------
NAR_DAILY_RACE_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"
NAR_MONTHLY_RACE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload"
    "?type=monthly&k_year={year}&k_month={month}"
)

def _default_data_root() -> Path:
    env=os.getenv("KEIBA_DATA_DIR","").strip()
    if env:return Path(env)
    for cand in (Path("/var/data/keiba_data"),Path("/data/keiba_data")):
        try:
            if cand.parent.exists() and os.access(cand.parent,os.W_OK):
                return cand
        except Exception:pass
    return Path("/tmp/keiba_data")

DATA_ROOT = _default_data_root()
ARCHIVE_DIR = DATA_ROOT / "nar" / "archives"
DB_PATH = DATA_ROOT / "nar" / "nar.sqlite3"
PREPARED_DB_PATH = DATA_ROOT / "prepared" / "prepared.sqlite3"
RACEDB_PATH = Path(os.getenv("RACEDB_PATH", str(DATA_ROOT / "racedb" / "racedb.sqlite3")))
DAY_BUNDLE_DB_PATH = Path(os.getenv("DAY_BUNDLE_DB_PATH", str(DATA_ROOT / "bundle" / "day_bundle.sqlite3")))

# Official CSV fixed-column indexes, based on NAR's published data specification.
RACE_IDX = {
    "track": 0,
    "date": 1,
    "race_no": 2,
    "start_time": 3,
    "race_type": 4,
    "title": 5,
    "surface": 21,
    "direction": 22,
    "distance": 23,
    "weather": 24,
    "condition": 25,
    "field_size": 26,
    "class_condition": 27,
    "prize1": 28,
    "prize2": 29,
    "prize3": 30,
    "prize4": 31,
    "prize5": 32,
    "corner_name_start": 50,
    "corner_order_start": 58,
}
HORSE_IDX = {
    "track": 0,
    "date": 1,
    "race_no": 2,
    "frame_no": 3,
    "horse_no": 5,
    "name": 6,
    "sex": 7,
    "age": 8,
    "jockey": 14,
    "carried_weight": 16,
    "trainer": 18,
    "finish": 31,
    "time": 32,
}


from arvexq.normalize.scalars import (
    _clean,
    _int,
    _float,
    _carried_weight,
    _iso_date,
    _start_time,
    _time_seconds,
    _normalize_sex,
    _scratch_status,
    _normalize_weather,
    _normalize_condition,
    _stable_id,
)


from arvexq.ingest.parsers.nar_archive import (
    read_csv_from_zip,
    strip_header,
    _top_level_tokens,
    parse_corner_order,
)


@dataclass
class RaceRow:
    track: str
    date: str
    race_no: int
    start_time: str
    title: str
    distance: int
    weather: str
    condition: str
    field_size: int
    prize: tuple[int, int, int, int, int]
    corners: list[dict[int, int]]


@dataclass
class EntryRow:
    track: str
    date: str
    race_no: int
    frame_no: int
    horse_no: int
    name: str
    sex: str
    age: int
    carried_weight: float
    jockey: str
    trainer: str
    finish: int
    time_seconds: float


# ARVEXQ_EXTRACTED:install_legacy_stores
from arvexq.infra.legacy_stores import install_legacy_stores as _arvexq_installer
_arvexq_installer(globals())
del _arvexq_installer


from arvexq.normalize.central_feed import (
    normalize_central_race,
)



def _jra_request(url: str, cname: str | None = None, cache_sec: int = 1800) -> str:
    return _acq_central_jra_transport._jra_request(
        url, cname, cache_sec,
    )

def _jra_norm_cname(value:str)->str:
    return _acq_central_jra_identifiers._jra_norm_cname(
        value,
    )

def _jra_attr_cname(tag, pattern) -> str:
    return _acq_central_jra_identifiers._jra_attr_cname(
        tag, pattern,
        _jra_norm_cname=_jra_norm_cname,
    )


def _jra_program_title(info:str)->str:
    return _acq_central_jra_identifiers._jra_program_title(
        info,
    )

def _jra_program_summaries(iso_date:str)->list[dict]:
    return _acq_central_jra_program._jra_program_summaries(
        iso_date,
        _jra_program_title=_jra_program_title, _jra_request=_jra_request, _jra_text=_jra_text,
        _today_iso=_today_iso,
    )

def _jra_program_lookup(iso_date:str,track:str,race_no:int):
    return _acq_central_jra_program._jra_program_lookup(
        iso_date, track, race_no,
        _jra_program_summaries=_jra_program_summaries,
    )

def _jra_find_cname(iso_date:str,track:str,race_no:int)->str:
    return _acq_central_jra_program._jra_find_cname(
        iso_date, track, race_no,
        _jra_norm_cname=_jra_norm_cname, _jra_race_no_from_cname=_jra_race_no_from_cname, _jra_request=_jra_request,
        _jra_track_from_cname=_jra_track_from_cname,
    )

def _jra_text(tag) -> str:
    return _acq_central_jra_identifiers._jra_text(
        tag,
    )

def _jra_iso_date(y:int,m:int,d:int)->str:
    return _acq_central_jra_identifiers._jra_iso_date(
        y, m, d,
    )

def _jra_date_from_cname(cname:str)->str:
    return _acq_central_jra_identifiers._jra_date_from_cname(
        cname,
    )

def _jra_race_no_from_cname(cname:str)->int:
    return _acq_central_jra_identifiers._jra_race_no_from_cname(
        cname,
    )

def _jra_track_from_cname(cname:str)->str:
    return _acq_central_jra_identifiers._jra_track_from_cname(
        cname,
    )

def _jra_parse_time_seconds(txt:str)->float:
    return _acq_central_jra_identifiers._jra_parse_time_seconds(
        txt,
    )

def _jra_parse_past_cell(cell, cutoff:str) -> dict | None:
    return _acq_central_jra_history._jra_parse_past_cell(
        cell, cutoff,
        _jra_attr_cname=_jra_attr_cname, _jra_iso_date=_jra_iso_date, _jra_parse_time_seconds=_jra_parse_time_seconds,
        _jra_text=_jra_text,
    )

def _jra_profile_runs(cname:str, cutoff:str, limit:int=5)->list[dict]:
    return _acq_central_jra_history._jra_profile_runs(
        cname, cutoff, limit,
        _jra_attr_cname=_jra_attr_cname, _jra_iso_date=_jra_iso_date, _jra_parse_time_seconds=_jra_parse_time_seconds,
        _jra_request=_jra_request, _jra_text=_jra_text,
    )

from arvexq.ingest.history.run_merge import (
    _jra_merge_run_fields,
    _jra_run_core_complete,
    _jra_history_complete,
    _jra_merge_runs,
    _merge_fast_history,
)


def _jra_parse_race(cname:str, supplement_profiles: bool = True)->dict|None:
    return _acq_central_jra_racecards._jra_parse_race(
        cname, supplement_profiles,
        _jra_attr_cname=_jra_attr_cname, _jra_date_from_cname=_jra_date_from_cname, _jra_norm_cname=_jra_norm_cname,
        _jra_parse_past_cell=_jra_parse_past_cell, _jra_profile_runs=_jra_profile_runs, _jra_program_lookup=_jra_program_lookup,
        _jra_race_no_from_cname=_jra_race_no_from_cname, _jra_request=_jra_request, _jra_text=_jra_text,
        _jra_track_from_cname=_jra_track_from_cname, _today_iso=_today_iso,
    )

def _jra_parse_race_summary(cname:str)->dict|None:
    return _acq_central_jra_racecards._jra_parse_race_summary(
        cname,
        _jra_date_from_cname=_jra_date_from_cname, _jra_program_lookup=_jra_program_lookup, _jra_race_no_from_cname=_jra_race_no_from_cname,
        _jra_request=_jra_request, _jra_text=_jra_text, _jra_track_from_cname=_jra_track_from_cname,
        _today_iso=_today_iso,
    )

def fetch_jra_official(iso_date:str, lightweight: bool = False)->list[dict]:
    return _acq_central_jra_calendar.fetch_jra_official(
        iso_date, lightweight,
        _jra_parse_race=_jra_parse_race, _jra_parse_race_summary=_jra_parse_race_summary, _jra_program_summaries=_jra_program_summaries,
        _jra_race_no_from_cname=_jra_race_no_from_cname, _jra_request=_jra_request, _jra_track_from_cname=_jra_track_from_cname,
    )

def fetch_central_feed(iso_date: str, history: bool = False) -> list[dict]:
    # Prefer a licensed feed when configured. Otherwise use the official JRA website.
    return _acq_central_feeds.fetch_central_feed(
        iso_date, history,
        fetch_jra_official=fetch_jra_official,
    )

from arvexq.ingest.scheduling import (
    iter_months_back,
    _race_minutes,
    _commercial_target_rows,
    _months_from_race_date,
    _race_minutes_server,
)


def sync_recent_history(months: int = 12) -> list[dict]:
    return _acq_local_archive.sync_recent_history(
        months,
        NarSync=NarSync,
    )


_history_lock = threading.Lock()
_history_started = False
_history_ready = False
_history_error = ""

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

def _now_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo"))

def _today_iso():
    return _now_jst().strftime("%Y-%m-%d")


@app.on_event("startup")
def _startup_history_backfill():
    # v43: targeted race prefetch is faster than a competing global crawl.
    if str(os.getenv("NAR_BACKGROUND_WARM", "0")).lower() in {"1","true","yes","on"}:
        ensure_history_async()


@app.get("/api/v1/storage-status")
def storage_status():
    p=DATA_ROOT
    return {
        "dataRoot":str(p),
        "persistentLikely":str(p).startswith("/var/data") or str(p).startswith("/data/"),
        "raceDb":str(RACEDB_PATH),
        "preparedDb":str(PREPARED_DB_PATH),
        "narDb":str(DB_PATH),
    }


@app.get("/health")
def health():
    try:
        nar_coverage = NarStore().coverage()
    except Exception:
        nar_coverage = {"minDate": None, "maxDate": None}
    try:
        central_coverage = CentralStore().coverage()
    except Exception:
        central_coverage = {"minDate": None, "maxDate": None, "count": 0}
    return {
        "status":"ok", "mode":"production-v325-home-race-boxes", "historyStarted":_history_started,
        "historyReady":_history_ready, "historyError":_history_error, "narCoverage":nar_coverage,
        "centralCoverage":central_coverage, "centralFeedConfigured":bool(os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback":True,
        "centralHistoryFeedConfigured":bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")),
        "narHistoryMonths": max(2, min(8, int(os.getenv("NAR_HISTORY_WARM_MONTHS", "4")))),
    }

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

@app.get("/api/v1/central-status")
def central_status():
    store = CentralStore()
    try:
        coverage = store.coverage()
    finally:
        store.conn.close()
    return {
        "feedConfigured": bool(os.getenv("CENTRAL_FEED_URL")),
        "historyFeedConfigured": bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback": True,
        "historyUsesLiveFeedFallback": bool(not os.getenv("CENTRAL_HISTORY_FEED_URL") and os.getenv("CENTRAL_FEED_URL")),
        "ingestEnabled": bool(os.getenv("CENTRAL_INGEST_TOKEN")),
        "coverage": coverage,
        "recentRuns": 5,
    }

@app.post("/api/v1/central-ingest")
async def central_ingest(request: Request):
    expected = _clean(os.getenv("CENTRAL_INGEST_TOKEN", ""))
    if not expected:
        raise HTTPException(status_code=503, detail="CENTRAL_INGEST_TOKEN is not configured")
    supplied = _clean(request.headers.get("X-Ingest-Token", ""))
    if supplied != expected:
        raise HTTPException(status_code=401, detail="invalid ingest token")
    body = await request.json()
    rows = body if isinstance(body, list) else body.get("races", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="races must be a list")
    count = CentralStore().upsert(rows)
    return {"status":"ok","stored":count}

@app.get("/api/v1/central-schema")
def central_schema():
    return {
      "description":"中央本番フィードの正規化JSON。JRA-VAN等のライセンス済みデータをこの形式へ変換して送信します。",
      "requiredRaceFields":["date","track","raceNumber","distance","horses"],
      "horseFields":["horseNumber","frameNumber","name","age","sex","carriedWeight","jockey","trainer","jockeyStats","trainerStats","prizeMoneyAtRace","recentRaces"],
      "recommendedRecentRaceDepth":5,
      "recommendedPastFields":["date","track","distance","condition","weather","fieldSize","finish","timeSeconds","cornerPositions","carriedWeight","racePrize1"],
      "optionalResult":{"status":"確定","finishers":[{"finish":1,"horseNumber":1,"name":"馬名","timeSeconds":92.3,"cornerPositions":[2,2,1]}]},
    }

_live_refresh_lock = threading.Lock()
_live_refresh_last: dict[str, int] = {}
_live_refresh_running: set[str] = set()

def _schedule_live_refresh(iso_date: str, force: bool = False):
    key = f"live:{iso_date}"
    now = int(time.time())
    with _live_refresh_lock:
        if key in _live_refresh_running or (not force and now - _live_refresh_last.get(key, 0) < 90):
            return
        _live_refresh_running.add(key)
    def worker():
        changed=False
        try:
            try:
                target = datetime.strptime(iso_date, "%Y-%m-%d").date()
                sync = NarSync()
                with _nar_sync_io_lock:
                    if iso_date == _today_iso():
                        sync.sync_daily(force=force)
                    else:
                        # Target only the selected month instead of a bulk history crawl.
                        sync.sync_month(target.year,target.month,force=force)
                changed=True
            except Exception as exc:
                print(f"NAR background sync failed: {exc}")
            if changed:
                # v48: an empty list may have been cached before the async NAR fetch finished.
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(iso_date+"|")]
        finally:
            with _live_refresh_lock:
                _live_refresh_running.discard(key)
                _live_refresh_last[key] = int(time.time())
    threading.Thread(target=worker, daemon=True).start()


_central_refresh_lock = threading.Lock()
_central_refresh_running: set[str] = set()
_central_refresh_last: dict[str, int] = {}

def _schedule_central_refresh(iso_date: str, force: bool = False):
    now=int(time.time())
    with _central_refresh_lock:
        if iso_date in _central_refresh_running:
            return
        # current day can refresh frequently; older dates are effectively immutable
        ttl=90 if iso_date==_today_iso() else 3600
        if not force and now-_central_refresh_last.get(iso_date,0)<ttl:
            return
        _central_refresh_running.add(iso_date)
    def worker():
        success=False
        try:
            if _clean(os.getenv("CENTRAL_FEED_URL", "")):
                rows=fetch_central_feed(iso_date)
            else:
                rows=fetch_jra_official(iso_date, lightweight=True)
                if not rows: rows=_netkeiba_race_summaries(iso_date)
            if rows:
                st=CentralStore()
                try: st.upsert(rows)
                finally: st.conn.close()
                success=True
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(iso_date+"|")]
        except Exception as exc:
            print(f"Central async refresh failed: {exc}")
        finally:
            with _central_refresh_lock:
                _central_refresh_running.discard(iso_date)
                # Successful fetches use the normal TTL. Empty/failed fetches retry quickly.
                _central_refresh_last[iso_date]=int(time.time()) if success else max(0,int(time.time())-85)
    threading.Thread(target=worker,daemon=True).start()


_commercial_collector_lock=threading.Lock()
_commercial_collector_state={
    "running":False,"lastStart":0,"lastFinish":0,"lastError":"",
    "hydrated":0,"diagnosed":0,"cycleSec":0,
}


def _commercial_collect_once():
    started=time.time()
    with _commercial_collector_lock:
        if _commercial_collector_state["running"]:return
        _commercial_collector_state.update({"running":True,"lastStart":started,"lastError":"","hydrated":0,"diagnosed":0})
    queued=ready=0;errs=[]
    try:
        today=_today_iso()
        _schedule_live_refresh(today,False)
        _schedule_central_refresh(today,False)
        # Short settle only; the next cycle catches anything still downloading.
        time.sleep(float(os.getenv("COMMERCIAL_LIST_SETTLE_SEC","1.2")))
        rows=[]
        try:rows.extend(nar_race_summaries(today))
        except Exception as exc:errs.append("NAR list: "+str(exc))
        try:rows.extend(central_race_summaries(today,allow_network=False))
        except Exception as exc:errs.append("JRA list: "+str(exc))
        nowj=_now_jst();now_min=nowj.hour*60+nowj.minute
        targets=_commercial_target_rows(rows,now_min)
        for idx,r in enumerate(targets):
            rid=str(r.get("id") or "")
            if not rid:continue
            d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            pm=(d or {}).get("preparedMeta") or {}
            if d and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady"):
                ready+=1;continue
            # Upcoming races first, but all jobs share the same two-worker queue.
            priority=20+idx
            _schedule_fast_card_refresh(rid,priority);queued+=1
        with _race_list_cache_lock:_race_list_cache.clear()
        _schedule_day_bundle_refresh(today,False)
    except Exception as exc:errs.append(str(exc))
    finally:
        finished=time.time()
        with _commercial_collector_lock:
            _commercial_collector_state.update({
                "running":False,"lastFinish":finished,"lastError":" | ".join(errs[-6:]),
                "hydrated":ready,"diagnosed":ready,"queued":queued,"cycleSec":round(finished-started,2),
            })

def _commercial_collector_loop():
    first_delay=float(os.getenv("COMMERCIAL_COLLECTOR_START_DELAY_SEC","1.0"))
    interval=max(120,int(os.getenv("COMMERCIAL_COLLECTOR_INTERVAL_SEC","180")))
    time.sleep(first_delay)
    while True:
        try:_commercial_collect_once()
        except Exception as exc:print("commercial collector cycle failed",exc)
        time.sleep(interval)

@app.on_event("startup")
def _start_commercial_collector():
    enabled=str(os.getenv("ARVEXQ_COMMERCIAL_COLLECTOR","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_commercial_collector_loop,daemon=True,name="arvexq-commercial-collector").start()

@app.get("/api/v1/runtime-status")
def runtime_status():
    with _fast_card_cv:
        queued=len(_fast_card_queue);running=len(_fast_card_running)
    with _commercial_collector_lock:collector=dict(_commercial_collector_state)
    return {
        "build":"v324","engine":PREDICTION_ENGINE_VERSION,"volatilityEngine":VOLATILITY_ENGINE_VERSION,"dataRoot":str(DATA_ROOT),
        "persistentLikely":str(DATA_ROOT).startswith("/var/data") or str(DATA_ROOT).startswith("/data/"),
        "fastCardQueue":queued,"fastCardRunning":running,"collector":collector,"siteBootstrap":True,"persistentDayBundle":True,"nonBlockingBootstrap":True,"autoOdds":True,
        "racedb":RACEDB.status(),
    }

@app.get("/api/v1/collector-status")
def collector_status():
    with _commercial_collector_lock:
        return dict(_commercial_collector_state)

def _central_refresh_status(iso_date: str) -> dict:
    with _central_refresh_lock:
        return {"running": iso_date in _central_refresh_running, "last": _central_refresh_last.get(iso_date,0)}

def _nar_month_needs_fetch(year: int, month: int) -> bool:
    return _acq_local_archive._nar_month_needs_fetch(
        year, month,
        NarStore=NarStore,
    )


def _download_nar_month_only(year: int, month: int) -> tuple[int, int, bytes, Path]:
    return _acq_local_archive._download_nar_month_only(
        year, month,
        ARCHIVE_DIR=ARCHIVE_DIR, NAR_MONTHLY_RACE_URL=NAR_MONTHLY_RACE_URL,
    )


def _sync_nar_month_wave(months: list[tuple[int, int]]) -> tuple[list[dict], list[str]]:
    # Download network-bound monthly ZIPs concurrently, then import sequentially into SQLite.
    # This keeps DB writes safe while removing the largest source of wait time.
    return _acq_local_archive._sync_nar_month_wave(
        months,
        NarSync=NarSync, _download_nar_month_only=_download_nar_month_only, _nar_month_needs_fetch=_nar_month_needs_fetch,
    )




def _history_counts(horse_names: list[str], cutoff: str) -> dict:
    return _acq_local_history._history_counts(
        horse_names, cutoff,
        NarStore=NarStore,
    )

def _start_race_history_search(race_id: str, iso_date: str, horse_names: list[str], force: bool = False) -> dict:
    return _acq_local_history._start_race_history_search(
        race_id, iso_date, horse_names, force,
        RACEDB=RACEDB, _build_fast_diagnosis_snapshot=_build_fast_diagnosis_snapshot, _detail_cache=_detail_cache,
        _detail_cache_lock=_detail_cache_lock, _history_counts=_history_counts, _supplement_sparse_nar_history=_supplement_sparse_nar_history,
        _sync_nar_month_wave=_sync_nar_month_wave,
    )

def _race_history_status(race_id: str) -> dict | None:
    return _acq_local_history._race_history_status(
        race_id,
    )

def _new_conn(path: Path):
    conn = sqlite3.connect(path, timeout=1.5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=1200")
    except Exception:
        pass
    return conn


def nar_race_summaries(iso_date: str) -> list[dict]:
    return _acq_local_racecards.nar_race_summaries(
        iso_date,
        DB_PATH=DB_PATH, _new_conn=_new_conn,
    )



def _netkeiba_get(url:str,timeout:float=4.0,cache_sec:int=45)->str:
    return _acq_netkeiba_transport._netkeiba_get(
        url, timeout, cache_sec,
    )

def _netkeiba_db_horse_history(name:str, cutoff:str, limit:int=5)->dict:
    return _acq_netkeiba_history._netkeiba_db_horse_history(
        name, cutoff, limit,
        _netkeiba_get=_netkeiba_get,
    )


def _supplement_sparse_nar_history(race_id:str, names:list[str], cutoff:str)->int:
    return _acq_netkeiba_history._supplement_sparse_nar_history(
        race_id, names, cutoff,
        _netkeiba_db_horse_history=_netkeiba_db_horse_history,
    )


def _netkeiba_race_summaries(iso_date:str)->list[dict]:
    return _acq_netkeiba_program._netkeiba_race_summaries(
        iso_date,
        _netkeiba_get=_netkeiba_get, _today_iso=_today_iso,
    )

def _netkeiba_program_race_id(iso_date:str,track:str,race_no:int)->str:
    return _acq_netkeiba_program._netkeiba_program_race_id(
        iso_date, track, race_no,
        _jra_program_lookup=_jra_program_lookup,
    )

def _netkeiba_race_id(iso_date:str,track:str,race_no:int)->str:
    return _acq_netkeiba_program._netkeiba_race_id(
        iso_date, track, race_no,
        _netkeiba_program_race_id=_netkeiba_program_race_id, _netkeiba_race_summaries=_netkeiba_race_summaries,
    )

from arvexq.ingest.parsers.supplemental import (
    _parse_recent_cell,
    _safe_float,
    _safe_int,
    _smart_normalize_row,
)

_NK_WAKU_RE = re.compile(r"^Waku(\d)$")
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\d{1,2})$")
_NK_SEXAGE_RE = re.compile(r"^(牡|牝|セ|騸)\s*(\d{1,2})")


def _nk_row_horse_no(tr, index: int | None = None) -> int:
    return _acq_netkeiba_rows._nk_row_horse_no(
        tr, index,
        _NK_ODDS_ID_RE=_NK_ODDS_ID_RE,
    )


def _nk_row_frame(tr) -> int:
    return _acq_netkeiba_rows._nk_row_frame(
        tr,
        _NK_WAKU_RE=_NK_WAKU_RE,
    )


def _nk_row_horse(tr, index: int | None = None) -> dict | None:
    return _acq_netkeiba_rows._nk_row_horse(
        tr, index,
        _NK_SEXAGE_RE=_NK_SEXAGE_RE, _nk_row_frame=_nk_row_frame, _nk_row_horse_no=_nk_row_horse_no,
    )


def _netkeiba_detail_rows(detail:dict)->list[dict]:
    return _acq_netkeiba_racecards._netkeiba_detail_rows(
        detail,
        _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id, _nk_row_horse=_nk_row_horse,
    )

def central_race_summaries(iso_date: str, allow_network: bool = False, force: bool = False) -> list[dict]:
    return _acq_central_racecards.central_race_summaries(
        iso_date, allow_network, force,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, CentralStore=CentralStore, _jra_program_summaries=_jra_program_summaries,
        _netkeiba_race_summaries=_netkeiba_race_summaries, _new_conn=_new_conn,
    )


def _nar_netkeiba_race_id(iso_date:str,track:str,race_no:int)->str:
    return _acq_netkeiba_program._nar_netkeiba_race_id(
        iso_date, track, race_no,
    )

def _nar_netkeiba_preview_rows(detail:dict,force:bool=False)->dict:
    return _acq_netkeiba_racecards._nar_netkeiba_preview_rows(
        detail, force,
        _nar_netkeiba_race_id=_nar_netkeiba_race_id, _netkeiba_get=_netkeiba_get,
    )


def _parse_nar_live_odds_html(html:str)->dict:
    return _acq_local_odds._parse_nar_live_odds_html(
        html,
    )


def _nar_live_odds(track:str,iso_date:str,race_no:int,force:bool=False)->dict:
    return _acq_local_odds._nar_live_odds(
        track, iso_date, race_no, force,
        _parse_nar_live_odds_html=_parse_nar_live_odds_html,
    )

def _attach_nar_live_odds(detail:dict)->dict:
    return _acq_local_odds._attach_nar_live_odds(
        detail,
        _nar_live_odds=_nar_live_odds,
    )

def nar_race_detail(race_id: str) -> dict | None:
    return _acq_local_racecards.nar_race_detail(
        race_id,
        NarStore=NarStore,
    )


def _nar_attach_recent_batch(detail: dict, limit: int = 5) -> dict:
    return _acq_local_history._nar_attach_recent_batch(
        detail, limit,
        DB_PATH=DB_PATH, _new_conn=_new_conn,
    )


from arvexq.ingest.history.central_rows import (
    _horse_key,
    _central_find_horse,
    _central_run_from_race,
)


def _central_resolve_race_id(run: dict) -> str:
    return _acq_central_history._central_resolve_race_id(
        run,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, _new_conn=_new_conn,
    )


def _central_recent_from_store(horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
    return _acq_central_history._central_recent_from_store(
        horse_name, cutoff, limit,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, _new_conn=_new_conn,
    )


def _merge_central_recent(existing: list[dict], stored: list[dict], cutoff: str, limit: int = 5) -> list[dict]:
    return _acq_central_history._merge_central_recent(
        existing, stored, cutoff, limit,
        _central_resolve_race_id=_central_resolve_race_id,
    )


def _central_month_dates(year: int, month: int, cutoff: str) -> list[str]:
    return _acq_central_history._central_month_dates(
        year, month, cutoff,
    )


def _fetch_central_days_parallel(days: list[str]) -> tuple[list[dict], list[str]]:
    return _acq_central_history._fetch_central_days_parallel(
        days,
        fetch_central_feed=fetch_central_feed,
    )


def _start_central_history_search(race_id: str, iso_date: str, force: bool = False) -> dict:
    return _acq_central_history._start_central_history_search(
        race_id, iso_date, force,
        CentralStore=CentralStore, _central_month_dates=_central_month_dates, _detail_cache=_detail_cache,
        _detail_cache_lock=_detail_cache_lock, _fetch_central_days_parallel=_fetch_central_days_parallel, _jra_profile_runs=_jra_profile_runs,
        central_race_detail=central_race_detail,
    )


from arvexq.ingest.parsers.market import (
    _parse_netkeiba_win_odds_payload,
    _parse_payouts,
)


def _netkeiba_live_win_odds(detail:dict,force:bool=False)->dict:
    return _acq_netkeiba_odds._netkeiba_live_win_odds(
        detail, force,
        _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id,
    )

def _merge_central_odds(detail:dict, odds:dict)->dict:
    return _acq_merge_current._merge_central_odds(
        detail, odds,
        _now_jst=_now_jst,
    )

def _merge_result_fields(detail:dict,result:dict)->dict:
    return _acq_merge_current._merge_result_fields(
        detail, result,
        _now_jst=_now_jst,
    )


def _fetch_nar_payouts_only(detail: dict) -> tuple[list[dict],str]:
    return _acq_local_results._fetch_nar_payouts_only(
        detail,
    )


def _attach_nar_payouts(detail: dict) -> dict:
    return _acq_local_results._attach_nar_payouts(
        detail,
        _fetch_nar_payouts_only=_fetch_nar_payouts_only,
    )


def _netkeiba_current_result(detail:dict)->dict|None:
    return _acq_netkeiba_results._netkeiba_current_result(
        detail,
        _jra_parse_time_seconds=_jra_parse_time_seconds, _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id,
    )


def _jra_result_cname_from_card(cname:str)->str:
    return _acq_central_jra_identifiers._jra_result_cname_from_card(
        cname,
        _jra_norm_cname=_jra_norm_cname, _jra_request=_jra_request,
    )

def _jra_any_track(cname:str)->str:
    return _acq_central_jra_identifiers._jra_any_track(
        cname,
    )

def _jra_any_race_no(cname:str)->int:
    return _acq_central_jra_identifiers._jra_any_race_no(
        cname,
    )

def _jra_parse_result(result_cname:str,base:dict|None=None)->dict|None:
    return _acq_central_jra_results._jra_parse_result(
        result_cname, base,
        _jra_any_race_no=_jra_any_race_no, _jra_any_track=_jra_any_track, _jra_date_from_cname=_jra_date_from_cname,
        _jra_parse_time_seconds=_jra_parse_time_seconds, _jra_request=_jra_request, _jra_text=_jra_text,
    )
def _netkeiba_race_meta(detail:dict)->dict:
    return _acq_netkeiba_racecards._netkeiba_race_meta(
        detail,
        _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id,
    )

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

def central_race_detail(race_id: str) -> dict | None:
    return _acq_central_racecards.central_race_detail(
        race_id,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, CentralStore=CentralStore, _central_recent_from_store=_central_recent_from_store,
        _jra_find_cname=_jra_find_cname, _jra_parse_race=_jra_parse_race, _jra_parse_result=_jra_parse_result,
        _jra_program_lookup=_jra_program_lookup, _jra_result_cname_from_card=_jra_result_cname_from_card, _merge_central_recent=_merge_central_recent,
        _netkeiba_current_result=_netkeiba_current_result, _netkeiba_detail_rows=_netkeiba_detail_rows, _netkeiba_program_race_id=_netkeiba_program_race_id,
        _netkeiba_race_meta=_netkeiba_race_meta, _new_conn=_new_conn, _race_should_have_result=_race_should_have_result,
    )

# --- v68 compact rows + fast JRA summaries; official data stays authoritative ---


def _format_feed_url(base:str,detail:dict)->str:
    return _acq_supplemental_feeds._format_feed_url(
        base, detail,
    )

def _fetch_json_url(url:str,timeout:float=4.0,token:str=""):
    return _acq_supplemental_feeds._fetch_json_url(
        url, timeout, token,
    )

def _extract_smartrc_embedded(html:str)->list[dict]:
    return _acq_supplemental_feeds._extract_smartrc_embedded(
        html,
    )

def _fetch_smartrc(detail:dict)->dict:
    return _acq_supplemental_feeds._fetch_smartrc(
        detail,
        _fetch_json_url=_fetch_json_url, _format_feed_url=_format_feed_url,
    )

def _fetch_extra_sources(detail:dict)->list[dict]:
    return _acq_supplemental_feeds._fetch_extra_sources(
        detail,
        _fetch_json_url=_fetch_json_url, _format_feed_url=_format_feed_url,
    )

def _merge_enrichment(detail:dict,data:dict)->dict:
    return _acq_merge_current._merge_enrichment(
        detail, data,
        _strip_excluded=_strip_excluded,
    )

def _enrichment_status(race_id:str)->dict:
    return _acq_supplemental_enrichment._enrichment_status(
        race_id,
    )

def _start_enrichment(race_id:str,detail:dict,force:bool=False,horse_no:int|None=None)->dict:
    return _acq_supplemental_enrichment._start_enrichment(
        race_id, detail, force, horse_no,
        PREPARED_STORE=PREPARED_STORE, RACEDB=RACEDB, _attach_evaluation_context=_attach_evaluation_context,
        _attach_stored_career=_attach_stored_career, _detail_cache=_detail_cache, _detail_cache_lock=_detail_cache_lock,
        _enrichment_status=_enrichment_status, _fetch_extra_sources=_fetch_extra_sources, _merge_enrichment=_merge_enrichment,
        _netkeiba_detail_rows=_netkeiba_detail_rows, _precompute_detail_metrics=_precompute_detail_metrics,
    )

def _apply_enrichment(race_id:str,detail:dict)->dict:
    return _acq_supplemental_enrichment._apply_enrichment(
        race_id, detail,
        _enrichment_status=_enrichment_status, _merge_enrichment=_merge_enrichment,
    )


# --- v123 live weather / going -----------------------------------------
_environment_lock=threading.Lock()
_environment_running:set[str]=set()
_environment_state:dict[str,dict]={}

def _env_clean_weather(v:str)->str:
    return _acq_environment_parsers._env_clean_weather(
        v,
    )

def _env_clean_condition(v:str)->str:
    return _acq_environment_parsers._env_clean_condition(
        v,
    )

def _parse_nar_environment_html(html:str)->dict:
    return _acq_environment_parsers._parse_nar_environment_html(
        html,
        _env_clean_condition=_env_clean_condition, _env_clean_weather=_env_clean_weather,
    )

def _parse_jra_environment_html(html:str, surface:str="")->dict:
    return _acq_environment_parsers._parse_jra_environment_html(
        html, surface,
        _env_clean_condition=_env_clean_condition, _env_clean_weather=_env_clean_weather, _jra_text=_jra_text,
    )

def _environment_http_get(url:str, ttl:int=30)->str:
    return _acq_environment_transport._environment_http_get(
        url, ttl,
    )

def _nar_fetch_environment(track:str, iso_date:str, race_no:int)->dict:
    return _acq_environment_providers._nar_fetch_environment(
        track, iso_date, race_no,
        _environment_http_get=_environment_http_get, _parse_nar_environment_html=_parse_nar_environment_html, _today_iso=_today_iso,
    )

def _jra_fetch_environment(row:dict)->dict:
    return _acq_environment_providers._jra_fetch_environment(
        row,
        _env_clean_condition=_env_clean_condition, _env_clean_weather=_env_clean_weather, _jra_find_cname=_jra_find_cname,
        _jra_request=_jra_request, _netkeiba_race_meta=_netkeiba_race_meta, _parse_jra_environment_html=_parse_jra_environment_html,
        _today_iso=_today_iso,
    )


def _upcoming_rows(rows:list[dict])->list[dict]:
    if not rows:return []
    if str(rows[0].get("date") or "")!=_today_iso():return rows
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    future=[r for r in rows if _race_minutes_server(r)>=nowm-12 and not _snapshot_final(r)]
    return future or [r for r in rows if not _snapshot_final(r)] or rows[-1:]

def _patch_nar_environment(date:str, track:str, rows:list[dict], env:dict)->list[str]:
    if not env:return []
    affected=[]
    upcoming=_upcoming_rows(rows)
    if not upcoming:return affected
    conn=_new_conn(DB_PATH)
    try:
        with conn:
            for r in upcoming:
                no=int(r.get("raceNumber") or 0)
                if not no:continue
                sets=[];args=[]
                if env.get("weather") not in (None,"","不明"):
                    sets.append("weather=?");args.append(env["weather"])
                if env.get("condition") not in (None,"","不明"):
                    sets.append("condition=?");args.append(env["condition"])
                if sets:
                    args.extend([track,date,no])
                    conn.execute("UPDATE races SET "+",".join(sets)+" WHERE track=? AND date=? AND race_no=?",args)
                    affected.append(str(r.get("id") or f"nar-{date}-{track}-{no:02d}"))
                scratch_map=env.get("scratchMap") or {}
                if scratch_map and int(env.get("raceNo") or 0)==no:
                    for horse_no,status in scratch_map.items():
                        conn.execute("UPDATE entries SET status=? WHERE track=? AND date=? AND race_no=? AND horse_no=?",
                                     (str(status),track,date,no,int(horse_no)))
                    rid=str(r.get("id") or f"nar-{date}-{track}-{no:02d}")
                    if rid not in affected:affected.append(rid)
    finally:conn.close()
    return affected

def _patch_central_environment(rows:list[dict], env_by_surface:dict, weather:str)->list[str]:
    if not rows:return []
    upcoming=_upcoming_rows(rows)
    st=CentralStore();affected=[]
    try:
        for r in upcoming:
            z=dict(r)
            changed=False
            if weather not in (None,"","不明") and z.get("weather")!=weather:
                z["weather"]=weather;changed=True
            surf=str(z.get("surface") or "")
            cond=env_by_surface.get(surf) or (env_by_surface.get("芝") if surf=="障害" else None)
            if cond not in (None,"","不明") and z.get("condition")!=cond:
                z["condition"]=cond;changed=True
            if changed:
                z["environmentMeta"]={"source":"JRA公式優先","updatedAtEpoch":int(time.time())}
                st.upsert([z]);affected.append(str(z.get("id") or ""))
    finally:
        st.conn.close()
    return [x for x in affected if x]

def _refresh_track_environment(date:str,circuit:str,track:str,force:bool=False)->dict:
    key=f"{date}|{circuit}|{track}"
    with _environment_lock:
        state=_environment_state.get(key) or {}
        if state.get("running"):return dict(state)
        if not force and int(time.time())-int(state.get("updatedAtEpoch") or 0)<25:
            return dict(state)
        _environment_state[key]={"running":True,"updatedAtEpoch":int(state.get("updatedAtEpoch") or 0),"changed":0,"error":""}
    affected=[];error=""
    try:
        rows=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
        rows=[r for r in rows if str(r.get("track") or "")==str(track)]
        if not rows:return {"running":False,"changed":0}
        if circuit=="地方":
            reps=_upcoming_rows(rows)
            rep=reps[0] if reps else rows[0]
            env=_nar_fetch_environment(track,date,int(rep.get("raceNumber") or 0))
            if env:
                affected=_patch_nar_environment(date,track,rows,env)
        else:
            reps=_upcoming_rows(rows)
            by_surface={}
            weather="不明"
            for surf in ("芝","ダート","障害"):
                cand=next((r for r in reps if str(r.get("surface") or "")==surf),None)
                if not cand:continue
                env=_jra_fetch_environment(cand)
                if env.get("weather") not in (None,"","不明"):weather=env["weather"]
                if env.get("condition") not in (None,"","不明"):
                    by_surface[surf]=env["condition"]
                for k,v in (env.get("surfaceConditions") or {}).items():
                    if v not in (None,"","不明"):by_surface[k]=v
            affected=_patch_central_environment(rows,by_surface,weather)

        if affected:
            with _race_list_cache_lock:
                [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(date+"|")]
            # Only recalc races whose live environment actually changed.
            for rid in affected:
                try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
                except Exception as exc:print("environment diagnosis rebuild failed",rid,exc)
    except Exception as exc:
        error=str(exc);print("track environment refresh failed",date,circuit,track,exc)
    finally:
        with _environment_lock:
            _environment_state[key]={
                "running":False,"updatedAtEpoch":int(time.time()),"changed":len(affected),"error":error
            }
    return dict(_environment_state.get(key) or {})

def _schedule_track_environment(date:str,circuit:str,track:str,force:bool=False)->None:
    key=f"{date}|{circuit}|{track}"
    with _environment_lock:
        if key in _environment_running:return
        state=_environment_state.get(key) or {}
        if not force and int(time.time())-int(state.get("updatedAtEpoch") or 0)<25:return
        _environment_running.add(key)
    def worker():
        try:_refresh_track_environment(date,circuit,track,force)
        finally:
            with _environment_lock:_environment_running.discard(key)
    threading.Thread(target=worker,daemon=True,name="env-"+track).start()

def _environment_cycle():
    date=_today_iso()
    rows=[]
    try:rows.extend(nar_race_summaries(date))
    except Exception:pass
    try:rows.extend(central_race_summaries(date,allow_network=False))
    except Exception:pass
    groups=[]
    seen=set()
    for r in rows:
        key=(str(r.get("circuit") or ""),str(r.get("track") or ""))
        if not key[0] or not key[1] or key[1]=="帯広" or key in seen:continue
        seen.add(key);groups.append(key)
    for circuit,track in groups:
        _schedule_track_environment(date,circuit,track,False)

def _environment_loop():
    time.sleep(float(os.getenv("ENVIRONMENT_START_DELAY_SEC","0.8")))
    while True:
        try:_environment_cycle()
        except Exception as exc:print("environment cycle failed",exc)
        time.sleep(max(30,int(os.getenv("ENVIRONMENT_REFRESH_SEC","45"))))

@app.on_event("startup")
def _start_environment_collector():
    enabled=str(os.getenv("ARVEXQ_ENVIRONMENT_COLLECTOR","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_environment_loop,daemon=True,name="arvexq-environment").start()


# --- v82 prepared-race cache -------------------------------------------
# Race pages should not rebuild every horse's history/stat profile at tap time.
# We prepare complete display JSON in the background and serve that snapshot first.


from arvexq.normalize.measurements import (
    _safe_body_weight_value,
    _safe_carried_weight_value,
    _sanitize_horse_measurements,
)


PRERACE_AUDIT_VERSION = "arvexq-prerace-audit-v317-consensus-rebuild"
WINNER_LEARNING_VERSION = "arvexq-winner-learning-v309-circuit-date-blocked"
WINNER_LEARNING_MIN_RACES = max(100, int(os.getenv("WINNER_LEARNING_MIN_RACES", "120")))
WINNER_LEARNING_MIN_DAYS = max(6, int(os.getenv("WINNER_LEARNING_MIN_DAYS", "8")))
WINNER_LEARNING_MIN_DATA_QUALITY = max(0.25, min(0.85, float(os.getenv("WINNER_LEARNING_MIN_DATA_QUALITY", "0.45"))))
PRERACE_FREEZE_MINUTES = max(1, min(20, int(os.getenv("PRERACE_FREEZE_MINUTES", "10"))))
_WINNER_LEARNING_CACHE = {}
_WINNER_LEARNING_LOCK = threading.Lock()


def _prediction_clock_state(detail: dict) -> tuple[str, int | None]:
    """Return (state, minutes_to_post). Never infer a lock after the race has started."""
    d=str((detail or {}).get("date") or "")
    st=str((detail or {}).get("startTime") or (detail or {}).get("scheduledStartTime") or "")
    if not d:return "unknown",None
    today=_today_iso()
    if d<today:return "started",None
    if d>today:return "future",None
    m=re.match(r"^(\d{1,2}):(\d{2})",st)
    if not m:return "unknown",None
    post=int(m.group(1))*60+int(m.group(2));now=_now_jst();nowm=now.hour*60+now.minute
    return ("pre" if nowm<post else "started"),post-nowm


from arvexq.backtest.probability_metrics import (
    _learning_probability,
    _learning_metric,
    _learning_paired_top1,
)


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

def _build_prerace_prediction(detail:dict)->dict|None:
    if not isinstance(detail,dict) or _snapshot_final(detail):return None
    state,minutes=_prediction_clock_state(detail)
    if state not in {"pre","future"}:return None
    horses=[h for h in (detail.get("horses") or []) if isinstance(h,dict) and int(h.get("horseNumber") or 0)>0 and not h.get("scratched") and not re.search(r"取消|除外|欠場",str(h.get("status") or ""))]
    if len(horses)<2:return None
    evals=[h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"),dict) else {} for h in horses]
    if sum(1 for e in evals if e)>=max(2,len(horses)//2):
        p1=_prob_vector([float(e.get("p1Score") or 0) for e in evals])
        p2=_prob_vector([float(e.get("p2Score") or 0) for e in evals])
        p3=_prob_vector([float(e.get("p3Score") or 0) for e in evals])
        cons=_prob_vector([float(e.get("winnerConsensusProbability") or 0) for e in evals])
    else:return None
    # ◎ is a betting-axis opinion for a top-three finish, not the top P1 head.
    # No forced ◎ and no swapping P1 values to match an axis selection.
    hon_idx=next((i for i,e in enumerate(evals) if str(e.get("mark") or "")=="◎"),None)
    decision=list(cons if any(cons) else p1)
    win_idx=max(range(len(decision)),key=lambda i:decision[i])
    win_e=evals[win_idx]
    rows=[]
    completeness=[]
    for i,(h,e) in enumerate(zip(horses,evals)):
        try:dc=max(0.0,min(1.0,float(e.get("dataCompleteness") or 0)/100.0))
        except Exception:dc=0.0
        completeness.append(dc)
        rows.append({
            "horseNumber":int(h.get("horseNumber") or 0),"name":str(h.get("name") or ""),"mark":str(e.get("mark") or ""),
            "decisionProbability":round(decision[i],8),"p1Probability":round(p1[i],8),"p2Probability":round(p2[i],8),"p3Probability":round(p3[i],8),
            "winnerConsensusProbability":round(cons[i],8),"pairwiseWinRate":round(float(e.get("pairwiseWinRate") or .5),8),
            "winEvidenceProbability":round(float(e.get("winEvidenceProbability") or 0),8),"axisConfidence":round(float(e.get("axisConfidence") or 0),8),
            "winnerDecisionStable":bool(e.get("winnerDecisionStable")),"score":round(float(e.get("score") or 0),3),"grade":str(e.get("grade") or ""),
            "axes":_audit_axes_from_eval(e),
        })
    now=int(time.time());quality=round(sum(completeness)/len(completeness),6) if completeness else 0.0
    mark_count=sum(1 for x in rows if x.get("mark"))
    payload={
        "version":PRERACE_AUDIT_VERSION,"modelVersion":AI_EVALUATION_VERSION,"predictionEngine":PREDICTION_ENGINE_VERSION,
        "circuitMethod":_v312_method(str(detail.get("circuit") or "")).get("id"),
        "raceId":str(detail.get("id") or ""),"raceDate":str(detail.get("date") or ""),"circuit":str(detail.get("circuit") or ""),
        "track":str(detail.get("track") or ""),"raceNumber":int(detail.get("raceNumber") or 0),"startTime":str(detail.get("startTime") or ""),
        "capturedAtEpoch":now,"capturedAtJst":_now_jst().isoformat(timespec="seconds"),"minutesToPost":minutes,
        "winnerNo":int(horses[win_idx].get("horseNumber") or 0),"winnerProbability":round(decision[win_idx],8),
        "honmeiHorseNumber":int(horses[hon_idx].get("horseNumber") or 0) if hon_idx is not None else 0,
        "winnerConfidence":round(float(win_e.get("axisConfidence") or 0),8),
        "winnerStable":bool(win_e.get("winnerDecisionStable")),
        "fieldSize":len(rows),"markCount":mark_count,"dataQuality":quality,"horses":rows,
        "marketIndependent":True,"oddsStored":False,"status":"pre-race",
        "frozen":bool(state=="pre" and minutes is not None and minutes<=PRERACE_FREEZE_MINUTES),
        "freezeWindowMinutes":PRERACE_FREEZE_MINUTES,
        "learningProfile":{k:v for k,v in (detail.get("winnerLearningProfile") or {}).items() if k in {"version","profileId","active","circuit","races","weights","power","shrink","reason"}},
        "sameDayMarkProfile":{k:v for k,v in (detail.get("sameDayMarkProfile") or {}).items() if k in {"version","active","completed","markRaces","evidence","coverage","deficit","frontSignal","lateSignal","innerSignal","flowLabel","sourceRaces"}},
    }
    payload["revision"]=hashlib.sha1(json.dumps({"m":[(x["horseNumber"],x["mark"],x["decisionProbability"]) for x in rows],"q":quality},ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
    return payload


def _prediction_audit_from_lock(detail:dict)->dict|None:
    lock=(detail or {}).get("preRacePrediction")
    result=(detail or {}).get("result") or {}
    if not isinstance(lock,dict) or not isinstance(lock.get("horses"),list) or result.get("status")!="確定":return None
    finishers=[x for x in (result.get("finishers") or []) if isinstance(x,dict) and int(x.get("finish") or 0)>0]
    if not finishers:return None
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    winner=int(finishers[0].get("horseNumber") or 0);top3={int(x.get("horseNumber") or 0) for x in finishers[:3]}
    rows=[x for x in lock.get("horses") or [] if int(x.get("horseNumber") or 0)>0]
    by={int(x.get("horseNumber") or 0):x for x in rows};w=by.get(winner)
    hon=next((x for x in rows if str(x.get("mark") or "")=="◎"),None)
    if not hon or not w:return None
    valid_marks={"◎","○","▲","☆+","☆","△","注+","注"}
    mark=str(w.get("mark") or "");marked=mark in valid_marks
    marked_nos={int(x.get("horseNumber") or 0) for x in rows if str(x.get("mark") or "") in valid_marks}
    podium_marked_count=len(top3 & marked_nos);podium_all_marked=len(top3)>=3 and podium_marked_count==3
    hit=int(hon.get("horseNumber") or 0)==winner
    ranked=sorted(rows,key=lambda x:(-float(x.get("decisionProbability") or 0),int(x.get("horseNumber") or 0)))
    winner_rank=next((i+1 for i,x in enumerate(ranked) if int(x.get("horseNumber") or 0)==winner),999)
    hp=max(1e-9,min(.999999,float(hon.get("decisionProbability") or 0)));wp=max(1e-9,min(.999999,float(w.get("decisionProbability") or 0)))
    brier=sum((float(x.get("decisionProbability") or 0)-(1.0 if int(x.get("horseNumber") or 0)==winner else 0.0))**2 for x in rows)
    axis_labels={"pure":"PURE","trueRun":"TRUE RUN","sectional":"SECTIONAL","positionScenario":"展開適合","conditions":"今回条件","opponentLevel":"相手レベル","stateConsistency":"状態・再現性"}
    diffs={}
    wa=w.get("axes") if isinstance(w.get("axes"),dict) else {};ha=hon.get("axes") if isinstance(hon.get("axes"),dict) else {}
    for k in axis_labels:
        try:diffs[k]=round(float(wa.get(k) or 0)-float(ha.get(k) or 0),6)
        except Exception:diffs[k]=0.0
    frag_gap=float(ha.get("fragility") or 0)-float(wa.get("fragility") or 0)
    if hit:reason="的中"
    elif frag_gap>=.08:reason="◎の脆さを過小評価"
    else:
        best_key=max(diffs,key=lambda k:diffs[k]) if diffs else ""
        best_val=diffs.get(best_key,0)
        if best_val>=.035:reason=axis_labels.get(best_key,best_key)+"を過小評価"
        elif hp-wp<=.03:reason="僅差順位"
        elif marked:reason="候補内の1着順位付け"
        else:reason="候補抽出"
    return {
        "version":PRERACE_AUDIT_VERSION,"raceId":str(detail.get("id") or ""),"raceDate":str(detail.get("date") or ""),"circuit":str(detail.get("circuit") or ""),"track":str(detail.get("track") or ""),"raceNumber":int(detail.get("raceNumber") or 0),"dataQuality":round(float(lock.get("dataQuality") or 0),6),"winnerNo":winner,"honNo":int(hon.get("horseNumber") or 0),
        "honHit":hit,"winnerMarked":marked,"winnerMark":mark,"winnerRank":winner_rank,"top2Hit":winner_rank<=2,"top3Hit":winner_rank<=3,
        "podiumAllMarked":podium_all_marked,"podiumMarkedCount":podium_marked_count,"markCount":int(lock.get("markCount") or 0),
        "honProbability":round(hp,8),"winnerProbability":round(wp,8),"probabilityGap":round(hp-wp,8),
        "winnerConfidence":round(float(lock.get("winnerConfidence") or 0),8),"winnerStable":bool(lock.get("winnerStable")),
        "highConfidence":float(lock.get("winnerConfidence") or 0)>=.70,"brier":round(brier,8),"logLoss":round(-math.log(wp),8),
        "missClass":"hit" if hit else ("candidate-order" if marked else "candidate-miss"),"reason":reason,"axisDiffs":diffs,
        "lockedAtEpoch":int(lock.get("capturedAtEpoch") or 0),"modelVersion":str(lock.get("modelVersion") or ""),
        "learningProfileId":str((lock.get("learningProfile") or {}).get("profileId") or "baseline"),"learningActive":bool((lock.get("learningProfile") or {}).get("active")),
        "top3Finishers":[int(x.get("horseNumber") or 0) for x in finishers[:3]],
    }


def _attach_prerace_audit(detail:dict)->dict:
    if not isinstance(detail,dict):return detail
    state,_=_prediction_clock_state(detail)
    current=detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"),dict) else None
    if state in {"pre","future"} and not _snapshot_final(detail):
        # Once the final pre-race window has been captured, never rewrite it.
        # This keeps the audit/training label immutable even if later refreshes arrive.
        if not (current and current.get("frozen")):
            fresh=_build_prerace_prediction(detail)
            if fresh:
                old_q=float((current or {}).get("dataQuality") or 0)
                new_q=float(fresh.get("dataQuality") or 0)
                entering_freeze=bool(fresh.get("frozen"))
                # In the freeze window, prefer the latest snapshot unless it is badly sparser.
                if not current or (entering_freeze and new_q+.08>=old_q) or (not entering_freeze and new_q+.02>=old_q):
                    detail["preRacePrediction"]=fresh
    if _snapshot_final(detail) and isinstance(detail.get("preRacePrediction"),dict):
        audit=_prediction_audit_from_lock(detail)
        if audit:detail["predictionAudit"]=audit
    return detail


def _compact_display_snapshot(detail: dict) -> dict:
    """Display JSON only; full career remains in RaceDB.past_runs."""
    if not isinstance(detail,dict):return detail
    detail=_attach_prerace_audit(detail)
    try:
        from arvexq.prediction.prerace_archive import evaluate_frozen_result
        frozen_audit=evaluate_frozen_result(detail)
        if frozen_audit:
            detail["frozenPredictionAudit"]=frozen_audit
    except Exception as exc:
        print("Frozen forecast audit unavailable",detail.get("id"),type(exc).__name__)
    out=dict(detail)
    horses=[]
    for h in detail.get("horses",[]) or []:
        if not isinstance(h,dict):continue
        z=_sanitize_horse_measurements(h)
        runs=list(z.get("allPastRuns") or z.get("recentRaces") or [])
        z["recentRaces"]=runs[:5]
        z.pop("allPastRuns",None)
        z.pop("evaluationSources",None)
        horses.append(z)
    out["horses"]=horses
    pm=dict(out.get("preparedMeta") or {})
    pm["displayCompact"]=True
    out["preparedMeta"]=pm
    try:
        out["dataCoreHealth"]=_data_core_health(out);out["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION
    except Exception:pass
    return out


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

def _data_core_active_horses(detail:dict)->list[dict]:
    return [h for h in (detail.get("horses") or []) if isinstance(h,dict) and not h.get("scratched") and int(h.get("horseNumber") or 0)>0]

def _data_core_result_due(detail:dict)->bool:
    try:
        if str(detail.get("date") or "")!=_today_iso():return True
        st=_race_minutes_server(detail)
        if st>=9999:return False
        now=_now_jst();return now.hour*60+now.minute>=st+2
    except Exception:return False

def _data_core_health(detail:dict|None)->dict:
    d=detail if isinstance(detail,dict) else {}
    horses=_data_core_active_horses(d); total=len(horses)
    field_size=max(total,int(d.get("fieldSize") or 0))
    named=sum(1 for h in horses if str(h.get("name") or "").strip() and str(h.get("jockey") or "").strip())
    card_pct=int(round(100*named/max(1,field_size))) if field_size else 0
    card_ready=bool(field_size>=2 and named>=max(2,field_size-1))

    hist_counts=[]
    for h in horses:
        if h.get("debutNoHistory"):
            hist_counts.append(5)
        else:
            runs=[x for x in (h.get("recentRaces") or h.get("allPastRuns") or []) if isinstance(x,dict)]
            hist_counts.append(min(5,len(runs)))
    hist_total=max(1,total*5)
    hist_points=sum(hist_counts)
    hist_pct=int(round(100*hist_points/hist_total)) if total else 0
    history_ready=bool(total and all(x>=5 for x in hist_counts))

    real_odds=[]
    weights=[]
    for h in horses:
        try:odd=float(h.get("winOdds") or 0)
        except Exception:odd=0.0
        real_odds.append(bool(odd>1 and not h.get("oddsForecast") and not re.search(r"予想|forecast",str(h.get("oddsSource") or ""),re.I)))
        try:bw=int(h.get("bodyWeight") or 0)
        except Exception:bw=0
        weights.append(bool(250<=bw<=800))
    odds_pct=int(round(100*sum(real_odds)/max(1,total))) if total else 0
    body_pct=int(round(100*sum(weights)/max(1,total))) if total else 0
    clock_state,minutes_to_post=_prediction_clock_state(d)
    is_today=str(d.get("date") or "")==_today_iso()
    odds_due=bool((not is_today) or clock_state=="started" or minutes_to_post is None or minutes_to_post<=360 or any(real_odds))
    body_due=bool((not is_today) or clock_state=="started" or minutes_to_post is None or minutes_to_post<=120 or any(weights))

    weather=str(d.get("weather") or "").strip();condition=str(d.get("condition") or "").strip()
    env_ready=weather not in ("","不明","—") and condition not in ("","不明","—")
    env_pct=(50 if weather not in ("","不明","—") else 0)+(50 if condition not in ("","不明","—") else 0)

    result=d.get("result") if isinstance(d.get("result"),dict) else {}
    finishers=[x for x in (result.get("finishers") or []) if isinstance(x,dict)]
    ranks={int(x.get("finish") or 0) for x in finishers}
    result_ready=all(x in ranks for x in (1,2,3))
    final=bool(str(result.get("status") or "")=="確定" or _snapshot_final(d))
    payouts=result.get("payouts") if isinstance(result.get("payouts"),list) else []
    payouts_ready=bool(payouts)
    due=_data_core_result_due(d)

    pm=d.get("preparedMeta") if isinstance(d.get("preparedMeta"),dict) else {}
    analysis_ready=bool(pm.get("diagnosisReady") and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION)

    srcs=[str(x) for x in (d.get("dataSources") or []) if x]
    default_source=" / ".join(srcs[:4]) or str(d.get("source") or "")
    def rec(status,pct,source="",note=""):
        return {"status":status,"completeness":max(0,min(100,int(pct))),"source":source or default_source,"note":note}
    return {
        "card":rec("ready" if card_ready else "missing",card_pct,note=f"{named}/{field_size or total}頭 基本項目"),
        "history":rec("ready" if history_ready else ("partial" if hist_points else "missing"),hist_pct,note=f"{hist_points}/{total*5 if total else 0}走"),
        "odds":rec("ready" if total and all(real_odds) else (("partial" if any(real_odds) else "missing") if odds_due else "not_due"),odds_pct,str(d.get("oddsSource") or default_source),f"{sum(real_odds)}/{total}頭 実単勝"+(" / 取得時間前" if not odds_due else "")),
        "body_weight":rec("ready" if total and all(weights) else (("partial" if any(weights) else "missing") if body_due else "not_due"),body_pct,note=f"{sum(weights)}/{total}頭 現在馬体重"+(" / 発表時間前" if not body_due else "")),
        "environment":rec("ready" if env_ready else ("partial" if env_pct else "missing"),env_pct,note=f"天候 {weather or '—'} / 馬場 {condition or '—'}"),
        "result":rec("ready" if result_ready else ("pending" if due else "not_due"),100 if result_ready else 0,str(result.get("source") or default_source),"上位3頭" if result_ready else "確定待ち"),
        "payouts":rec("ready" if payouts_ready else ("pending" if final else "not_due"),100 if payouts_ready else 0,str(result.get("payoutSource") or default_source),f"{len(payouts)}件" if payouts_ready else "確定待ち"),
        "analysis":rec("ready" if analysis_ready else "missing",100 if analysis_ready else 0,note=str(pm.get("diagnosisVersion") or "")),
    }

def _data_core_health_hash(field_key:str, item:dict)->str:
    raw=json.dumps([field_key,item.get("status"),item.get("completeness"),item.get("source"),item.get("note")],ensure_ascii=False,separators=(",",":"))
    return hashlib.sha1(raw.encode("utf-8","ignore")).hexdigest()

def _data_core_store_health(detail:dict|None, attempted:set[str]|None=None, source_hint:str="")->dict:
    if not isinstance(detail,dict) or not detail.get("id"):return {}
    rid=str(detail.get("id")); health=_data_core_health(detail); now=int(time.time()); attempted=attempted or set()
    conn=sqlite3.connect(RACEDB.path,timeout=3)
    try:
        for key,item in health.items():
            src=str(item.get("source") or source_hint or "")[:180]
            status=str(item.get("status") or "missing")
            pct=int(item.get("completeness") or 0)
            note=str(item.get("note") or "")[:400]
            vh=_data_core_health_hash(key,item)
            row=conn.execute("SELECT attempts FROM field_state WHERE race_id=? AND field_key=?",(rid,key)).fetchone()
            attempts=int(row[0] or 0) if row else 0
            if key in attempted and status!="ready":attempts+=1
            conn.execute("""INSERT INTO field_state(race_id,field_key,status,completeness,source,updated_at,last_attempt_at,attempts,note,value_hash)
                            VALUES(?,?,?,?,?,?,?,?,?,?)
                            ON CONFLICT(race_id,field_key) DO UPDATE SET status=excluded.status,completeness=excluded.completeness,
                            source=CASE WHEN excluded.source<>'' THEN excluded.source ELSE field_state.source END,
                            updated_at=excluded.updated_at,last_attempt_at=excluded.last_attempt_at,attempts=excluded.attempts,note=excluded.note,value_hash=excluded.value_hash""",
                         (rid,key,status,pct,src,now,now if key in attempted else 0,attempts,note,vh))
        conn.commit()
    finally:conn.close()
    return health

def _data_core_record_run(run_id:str,race_id:str,started:int,status:str,attempted:set[str],before:dict,after:dict,note:str=""):
    conn=sqlite3.connect(RACEDB.path,timeout=3)
    try:
        conn.execute("""INSERT OR REPLACE INTO collector_runs(run_id,race_id,started_at,finished_at,status,attempted_fields,before_json,after_json,note)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                     (run_id,race_id,started,int(time.time()),status,json.dumps(sorted(attempted),ensure_ascii=False),
                      json.dumps(before,ensure_ascii=False,separators=(",",":")),json.dumps(after,ensure_ascii=False,separators=(",",":")),str(note or "")[:600]))
        conn.commit()
    finally:conn.close()

def _data_core_snapshot(race_id:str)->dict|None:
    return _prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)

def _data_core_refresh_race(race_id:str,force:bool=False)->dict:
    rid=str(race_id or "")
    if not rid:return {"raceId":rid,"ok":False,"error":"empty race id"}
    with _data_core_lock:
        if rid in _data_core_running:
            d=_data_core_snapshot(rid);return {"raceId":rid,"ok":True,"running":True,"health":_data_core_health(d)}
        _data_core_running.add(rid)
    started=int(time.time());run_id=f"dc-{started}-{hashlib.sha1(rid.encode()).hexdigest()[:8]}";attempted=set();errors=[]
    try:
        d=_data_core_snapshot(rid)
        before=_data_core_health(d)
        # Card: hydrate only when basic starter rows are incomplete.
        if force or before.get("card",{}).get("status")!="ready":
            attempted.add("card")
            try:_hydrate_fast_card_now(rid,deep_history=False)
            except Exception as exc:errors.append("card:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        # Live odds + current body weight are one official/live fetch but tracked separately.
        if str((d or {}).get("date") or "")==_today_iso() and (force or h.get("odds",{}).get("status")!="ready" or h.get("body_weight",{}).get("status")!="ready"):
            attempted.update({"odds","body_weight"})
            try:odds_refresh(rid,1)
            except Exception as exc:errors.append("live:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if force or h.get("environment",{}).get("status")!="ready":
            attempted.add("environment")
            try:
                if rid.startswith("jra-"):
                    fresh=central_race_detail(rid)
                    if fresh:
                        base=d or fresh
                        for k in ("weather","condition","title","distance","surface","startTime","scheduledStartTime"):
                            if fresh.get(k) not in (None,"",0,"不明"):base[k]=fresh.get(k)
                        RACEDB.upsert_race(base);PREPARED_STORE.put(base,force=True);d=base
                else:
                    _schedule_track_environment(str((d or {}).get("date") or _today_iso()),str((d or {}).get("circuit") or "地方"),str((d or {}).get("track") or ""),True)
            except Exception as exc:errors.append("env:"+str(exc))

        h=_data_core_health(d)
        if force or h.get("history",{}).get("status")!="ready":
            attempted.add("history")
            try:
                if rid.startswith("jra-"):
                    _start_central_history_search(rid,str((d or {}).get("date") or _today_iso()),force=bool(force))
                else:
                    names=[str(x.get("name") or "") for x in ((d or {}).get("horses") or []) if x.get("name")]
                    if names:_start_race_history_search(rid,str((d or {}).get("date") or _today_iso()),names,force=bool(force))
            except Exception as exc:errors.append("history:"+str(exc))

        h=_data_core_health(d)
        if _data_core_result_due(d or {}) and (force or h.get("result",{}).get("status")!="ready"):
            attempted.add("result")
            try:_refresh_result_fast(rid)
            except Exception as exc:errors.append("result:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if h.get("result",{}).get("status")=="ready" and (force or h.get("payouts",{}).get("status")!="ready"):
            attempted.add("payouts")
            try:payout_refresh(rid)
            except Exception as exc:errors.append("payouts:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if force or h.get("analysis",{}).get("status")!="ready":
            attempted.add("analysis")
            try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
            except Exception as exc:errors.append("analysis:"+str(exc))
            d=_data_core_snapshot(rid)

        after=_data_core_store_health(d,attempted,"ARVEXQ Data Core")
        if isinstance(d,dict) and d.get("id"):
            d["dataCoreHealth"]=after;d["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION;d["dataCoreUpdatedAt"]=int(time.time())
            try:RACEDB.upsert_race(d);PREPARED_STORE.put(d,force=True)
            except Exception as exc:errors.append("persist-health:"+str(exc))
        _data_core_record_run(run_id,rid,started,"partial" if errors else "ok",attempted,before,after," | ".join(errors[-5:]))
        return {"raceId":rid,"ok":not errors,"attempted":sorted(attempted),"health":after,"errors":errors[-5:],"version":ARVEXQ_DATA_CORE_VERSION}
    finally:
        with _data_core_lock:_data_core_running.discard(rid)

def _data_core_day_rows(date:str)->list[dict]:
    try:return _bootstrap_rows_local(date)
    except Exception:return []

def _data_core_day_status(date:str,circuit:str="")->dict:
    rows=[r for r in _data_core_day_rows(date) if not circuit or str(r.get("circuit") or "")==str(circuit)]
    ids=[str(r.get("id") or "") for r in rows if r.get("id")]
    by={rid:{} for rid in ids}
    if ids:
        conn=sqlite3.connect(RACEDB.path,timeout=3);conn.row_factory=sqlite3.Row
        try:
            marks=",".join("?" for _ in ids)
            for r in conn.execute(f"SELECT * FROM field_state WHERE race_id IN ({marks})",ids).fetchall():
                by.setdefault(str(r["race_id"]),{})[str(r["field_key"])]=dict(r)
        finally:conn.close()
    fields={k:{"ready":0,"partial":0,"missing":0,"pending":0,"not_due":0} for k in DATA_CORE_FIELDS}
    ready_races=0
    race_rows=[]
    for r in rows:
        rid=str(r.get("id") or "");st=by.get(rid) or {}
        # If not yet persisted, calculate from the latest local snapshot without network.
        if not st:
            h=_data_core_health(_data_core_snapshot(rid))
            st={k:{"status":v.get("status"),"completeness":v.get("completeness"),"source":v.get("source"),"note":v.get("note")} for k,v in h.items()}
        for k in DATA_CORE_FIELDS:
            status=str((st.get(k) or {}).get("status") or "missing")
            fields[k][status if status in fields[k] else "missing"]+=1
        essential=("card","history","odds","body_weight","environment","analysis")
        ready=all(str((st.get(k) or {}).get("status") or "") in ({"ready","not_due"} if k in {"odds","body_weight"} else {"ready"}) for k in essential)
        if ready:ready_races+=1
        race_rows.append({"id":rid,"track":r.get("track"),"raceNumber":r.get("raceNumber"),"startTime":r.get("startTime"),"ready":ready,"fields":st})
    return {"version":ARVEXQ_DATA_CORE_VERSION,"date":date,"circuit":circuit,"raceCount":len(rows),"readyRaceCount":ready_races,"fields":fields,"races":race_rows}

def _data_core_cycle():
    global _data_core_state
    with _data_core_lock:
        if _data_core_state.get("running"):return
        _data_core_state.update({"running":True,"lastStart":int(time.time()),"checked":0,"refreshed":0,"error":""})
    checked=refreshed=0;errors=[]
    try:
        rows=_data_core_day_rows(_today_iso())
        nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
        candidates=[]
        for r in rows:
            rid=str(r.get("id") or "")
            if not rid:continue
            d=_data_core_snapshot(rid);h=_data_core_health(d);checked+=1
            _data_core_store_health(d,set(),"local") if d else None
            needed=[k for k in ("card","history","odds","body_weight","environment","analysis") if h.get(k,{}).get("status") not in {"ready","not_due"}]
            if _data_core_result_due(d or r) and h.get("result",{}).get("status")!="ready":needed.append("result")
            if h.get("result",{}).get("status")=="ready" and h.get("payouts",{}).get("status")!="ready":needed.append("payouts")
            if needed:
                st=_race_minutes_server(r);dist=abs(st-nowm) if st<9999 else 9999
                candidates.append((dist,st,rid,needed))
        candidates.sort(key=lambda x:(x[0],x[1]))
        targets=candidates[:max(1,int(os.getenv("ARVEXQ_DATA_CORE_BATCH","16")))]
        workers=max(1,min(8,len(targets))) if targets else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for z in pool.map(lambda x:_data_core_refresh_race(x[2],False),targets):
                    refreshed+=1
                    if not z.get("ok") and z.get("errors"):errors.extend(z.get("errors") or [])
    except Exception as exc:errors.append(str(exc))
    finally:
        with _data_core_lock:
            _data_core_state.update({"running":False,"lastFinish":int(time.time()),"checked":checked,"refreshed":refreshed,"error":" | ".join(errors[-5:])})

def _data_core_loop():
    time.sleep(float(os.getenv("ARVEXQ_DATA_CORE_START_DELAY_SEC","1.2")))
    while True:
        try:_data_core_cycle()
        except Exception as exc:print("ARVEXQ Data Core cycle failed",exc)
        time.sleep(max(10,int(os.getenv("ARVEXQ_DATA_CORE_LOOP_SEC","12"))))

@app.on_event("startup")
def _start_data_core_collector():
    enabled=str(os.getenv("ARVEXQ_DATA_CORE","1")).lower() in {"1","true","yes","on"}
    if enabled:threading.Thread(target=_data_core_loop,daemon=True,name="arvexq-data-core").start()

@app.get("/api/v1/data-core/status")
def data_core_status(date:str=Query(""),circuit:str=Query("")):
    ds=date or _today_iso();out=_data_core_day_status(ds,_clean(circuit))
    with _data_core_lock:out["collector"]=dict(_data_core_state)
    return out

@app.post("/api/v1/data-core/refresh/{race_id}")
def data_core_refresh(race_id:str,force:int=Query(1)):
    return _data_core_refresh_race(race_id,bool(force))

@app.post("/api/v1/data-core/refresh-day")
def data_core_refresh_day(date:str=Query(""),circuit:str=Query("")):
    ds=date or _today_iso();rows=[r for r in _data_core_day_rows(ds) if not circuit or str(r.get("circuit") or "")==str(circuit)]
    # Queue the full day without keeping the request open; the status endpoint exposes progress.
    def worker():
        ordered=sorted(rows,key=lambda r:_race_minutes_server(r))
        for r in ordered:
            rid=str(r.get("id") or "")
            if rid:
                try:_data_core_refresh_race(rid,True)
                except Exception as exc:print("data core day refresh failed",rid,exc)
    threading.Thread(target=worker,daemon=True,name="data-core-day-"+ds).start()
    return {"status":"queued","date":ds,"circuit":circuit,"raceCount":len(rows),"version":ARVEXQ_DATA_CORE_VERSION}


def _schedule_full_history_harvest(detail: dict) -> None:
    return _acq_history_harvest._schedule_full_history_harvest(
        detail,
        NarStore=NarStore, PREPARED_STORE=PREPARED_STORE, RACEDB=RACEDB,
        _attach_evaluation_context=_attach_evaluation_context, _attach_stored_career=_attach_stored_career, _jra_profile_runs=_jra_profile_runs,
        _precompute_detail_metrics=_precompute_detail_metrics, _today_iso=_today_iso,
    )

PREPARED_STORE = PreparedRaceStore()
_prewarm_lock = threading.Lock()
_prewarm_running: set[str] = set()
_prewarm_state: dict[str, dict] = {}


from arvexq.prediction.metrics.past_runs import (
    _pc_clamp,
    _pc_race_field,
    _pc_finish_quality,
    _pc_list_quality,
    _pc_style_metrics,
    _pc_sectional_score,
    _pc_fit_metrics,
)


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


def _ensure_race_volatility(detail: dict) -> dict:
    if not isinstance(detail,dict):return detail
    v=detail.get("volatility") or {}
    if v.get("version")!=VOLATILITY_ENGINE_VERSION:
        detail["volatility"]=_race_volatility(detail)
    return detail


def _restore_saved_odds(detail:dict)->dict:
    """Display-only odds must survive diagnosis/history/environment snapshot rebuilds."""
    if not isinstance(detail,dict):return detail
    race_id=str(detail.get("id") or "")
    if not race_id:return detail
    rows=[]
    try:rows=RACEDB.odds_latest(race_id) or []
    except Exception:rows=[]
    if not rows:
        try:
            previous,_=PREPARED_STORE.get(race_id)
            if previous:
                rows=[{
                    "horseNumber":h.get("horseNumber"),"winOdds":h.get("winOdds"),
                    "popularity":h.get("popularity"),"oddsSource":h.get("oddsSource") or previous.get("oddsSource")
                } for h in (previous.get("horses") or []) if h.get("winOdds") not in (None,"")]
                if rows:
                    detail["oddsUpdatedAt"]=previous.get("oddsUpdatedAt") or detail.get("oddsUpdatedAt")
                    detail["oddsSource"]=previous.get("oddsSource") or detail.get("oddsSource")
        except Exception:pass
    if not rows:return detail
    by={int(h.get("horseNumber") or 0):h for h in (detail.get("horses") or [])}
    latest=0;source=""
    for z in rows:
        no=int(z.get("horseNumber") or 0);h=by.get(no)
        if not h:continue
        for k in ("winOdds","popularity"):
            if z.get(k) not in (None,""):h[k]=z.get(k)
        if z.get("oddsSource"):
            h["oddsSource"]=z.get("oddsSource");source=z.get("oddsSource")
        latest=max(latest,int(z.get("capturedAt") or 0))
    if source:detail["oddsSource"]=source
    if latest:
        detail["oddsUpdatedAt"]=datetime.fromtimestamp(latest,ZoneInfo("Asia/Tokyo")).strftime("%H:%M:%S")
    return detail


def _precompute_detail_metrics(detail: dict) -> dict:
    detail = prepare_race_detail(detail)
    if not isinstance(detail,dict):return detail
    detail=_apply_enrichment(str(detail.get("id") or ""),detail)
    try:detail["trackSpeed"]=_pc_live_track_speed(detail)
    except Exception:detail["trackSpeed"]={"version":"track-speed-v300","score":0.5,"ratio":1.0,"evidence":0.0,"completed":0,"label":"基準","source":"fallback"}
    try:detail["winnerLearningProfile"]=_winner_learning_profile(detail)
    except Exception as exc:detail["winnerLearningProfile"]={"version":WINNER_LEARNING_VERSION,"active":False,"reason":"profile-error","error":str(exc)[:120]}
    for horse in detail.get("horses",[]) or []:
        runs=horse.get("allPastRuns") or horse.get("recentRaces") or []
        if detail.get("analysisMode")=="新馬" and not runs:horse["debutNoHistory"]=True
        horse["collectionState"]={"status":"complete" if runs or horse.get("debutNoHistory") else "basic" if horse.get("name") else "missing", "history":"not_applicable" if horse.get("debutNoHistory") and not runs else "available" if runs else "missing", "pastRunCount":len(runs)}
        metric_horse=dict(horse,recentRaces=[r for r in runs if _is_jump_run(r)]) if detail.get("analysisMode")=="障害" else dict(horse,recentRaces=runs)
        try:
            sectional,sectional_n=_pc_sectional_score(metric_horse,detail)
            if sectional is not None:
                horse["officialSectionalScore"]=round(sectional,6)
                horse["officialSectionalSamples"]=sectional_n
                # Prefer the reproducible past-run sectional signal over an opaque supplied lap score.
                horse["lapScore"]=round(sectional,6)
        except Exception:
            pass
        horse["integratedEvaluation"]=_integrated_evaluation(horse,detail)
        try:
            horse["precomputedMetrics"]={"style":_pc_style_metrics(metric_horse,detail),"fit":_pc_fit_metrics(metric_horse,detail),"sectional":{"score":horse.get("officialSectionalScore"),"samples":horse.get("officialSectionalSamples",0)}}
        except Exception:
            horse.setdefault("precomputedMetrics",{})
    _rank_evaluations(detail)
    detail["aiEvaluation"]={"version":AI_EVALUATION_VERSION,"horses":[{"horseNumber":h.get("horseNumber"),"name":h.get("name"),**h.get("integratedEvaluation",{})} for h in detail.get("horses",[])]}
    detail["volatility"]=_race_volatility(detail)
    detail.setdefault("preparedMeta",{})["metricsPrecomputed"]=True
    return detail


def _prepared_ttl(detail: dict) -> int:
    # Today's cards can change (odds/body weight/result). Old races are effectively static.
    return int(os.getenv("PREPARED_TODAY_TTL_SEC","45")) if str(detail.get("date") or "")==_today_iso() else int(os.getenv("PREPARED_ARCHIVE_TTL_SEC","21600"))


from arvexq.infra.snapshot_status import (
    _snapshot_final,
    _result_has_podium,
    _bootstrap_display_ready,
    _bootstrap_detail_ready,
    _merge_card_rows_preserve,
)


def _prepared_get_fresh(race_id: str) -> dict | None:
    detail,updated=PREPARED_STORE.get(race_id)
    if not detail or not updated or not _racedb_snapshot_usable(detail):return None
    if (detail.get("preparedMeta") or {}).get("fastPartial"):return detail
    if (detail.get("aiEvaluation") or {}).get("version")!=AI_EVALUATION_VERSION:
        detail=_precompute_detail_metrics(_strip_excluded(detail))
    detail=_ensure_race_volatility(detail)
    detail=_restore_saved_odds(detail)
    try:
        detail["dataCoreHealth"]=_data_core_health(detail);detail["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION
    except Exception:pass
    return detail


def _refresh_result_fast(race_id: str) -> dict | None:
    return _acq_snapshots_results._refresh_result_fast(
        race_id,
        _attach_nar_payouts=_attach_nar_payouts, _compact_display_snapshot=_compact_display_snapshot, _fast_local_race_detail=_fast_local_race_detail,
        _jra_find_cname=_jra_find_cname, _jra_parse_result=_jra_parse_result, _jra_result_cname_from_card=_jra_result_cname_from_card,
        _merge_result_fields=_merge_result_fields, _nar_official_result_fast=_nar_official_result_fast, _netkeiba_current_result=_netkeiba_current_result,
        _prepared_get_fresh=_prepared_get_fresh, _race_should_have_result=_race_should_have_result, _racedb_get_fast=_racedb_get_fast,
        _store_fast_snapshot=_store_fast_snapshot, central_race_detail=central_race_detail, nar_race_detail=nar_race_detail,
    )


def _prepare_race_snapshot(race_id: str, force: bool = False, manual: bool = False) -> dict | None:
    hit=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if hit and (str(hit.get("date") or "")<_today_iso() or _snapshot_final(hit)) and not force:return hit
    if hit and not force:return hit
    if manual and race_id.startswith("nar-"):
        match=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-",race_id)
        if match:
            target=datetime.strptime(match.group(1),"%Y-%m-%d")
            sync=NarSync()
            try:
                with _nar_sync_io_lock:
                    if match.group(1)==_today_iso():sync.sync_daily(force=True)
                    else:sync.sync_month(target.year,target.month,force=True)
            finally:sync.store.conn.close()
    detail=nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:return None
    horses=detail.get("horses") if isinstance(detail.get("horses"),list) else []
    if not race_id.startswith("nar-") and int(detail.get("fieldSize") or 0)>0 and not horses and not detail.get("result"):
        return None
    if race_id.startswith("nar-"):detail=_attach_nar_payouts(detail)
    if hit and hit.get("analysis"):detail["analysis"]=hit["analysis"]
    detail=_strip_excluded(_apply_enrichment(race_id,detail))
    detail=_attach_stored_career(detail)
    detail=_precompute_detail_metrics(_attach_evaluation_context(detail))
    detail=_restore_saved_odds(detail)
    detail.setdefault("preparedMeta",{}).pop("fastPartial",None)
    # Snapshot creation never blocks on network history. Existing DB/feed history is included.
    detail.setdefault("historySearch",{"status":"prepared","monthsDone":0,"maxMonths":0,"coverage":{"totalHorses":len(detail.get("horses",[])),"totalRuns":sum(len(h.get("recentRaces") or []) for h in detail.get("horses",[]))},"error":"","source":detail.get("source") or "prepared"})
    try:
        RACEDB.upsert_race(detail)
        _schedule_full_history_harvest(detail)
    except Exception as exc:print("RaceDB snapshot write failed",race_id,exc)
    PREPARED_STORE.put(detail,force=bool(manual or force))
    display=_compact_display_snapshot(detail)
    if detail.get("date")==_today_iso() and not _snapshot_final(detail):_schedule_detail_background_jobs(race_id,detail)
    return display


def _prewarm_sort_key(row: dict, date: str) -> tuple:
    t=str(row.get("startTime") or "")
    try:
        hh,mm=t.split(":",1);m=int(hh)*60+int(mm[:2])
    except Exception:
        m=9999
    if date==_today_iso():
        now=_now_jst().hour*60+_now_jst().minute
        return (0 if m>=now else 1, m if m>=now else m+1440, str(row.get("track") or ""), int(row.get("raceNumber") or 0))
    return (0,m,str(row.get("track") or ""),int(row.get("raceNumber") or 0))


def _schedule_prewarm(rows: list[dict], date: str, circuit: str = "") -> None:
    ordered=[r for r in sorted(rows,key=lambda x:_prewarm_sort_key(x,date)) if r.get("id") and (not circuit or r.get("circuit")==circuit)]
    max_races=max(1,int(os.getenv("PREWARM_MAX_RACES","36")))
    ordered=ordered[:max_races]
    if not ordered:return
    key=f"{date}|{circuit or 'all'}"
    with _prewarm_lock:
        if key in _prewarm_running:return
        _prewarm_running.add(key);_prewarm_state[key]={"running":True,"done":0,"total":len(ordered),"last":int(time.time()),"errors":0}
    def worker():
        done=errs=0
        workers=max(1,min(int(os.getenv("PREWARM_WORKERS","2")),len(ordered)))
        deep=max(0,int(os.getenv("PREWARM_DEEP_RACES","3")))
        def one(ix_row):
            ix,row=ix_row;rid=str(row.get("id") or "")
            detail=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            if detail:
                if not (_prepared_get_fresh(rid) or _racedb_get_fast(rid)):_store_fast_snapshot(detail)
            else:
                _schedule_fast_card_refresh(rid)
            return rid,detail
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(one,x) for x in enumerate(ordered)]
                for fut in as_completed(futures):
                    try:
                        _,detail=fut.result()
                        if detail:done+=1
                        else:errs+=1
                    except Exception as exc:
                        errs+=1;print("prewarm failed",exc)
                    with _prewarm_lock:_prewarm_state[key]={"running":True,"done":done,"total":len(ordered),"last":int(time.time()),"errors":errs}
        finally:
            with _prewarm_lock:
                _prewarm_running.discard(key);_prewarm_state[key]={"running":False,"done":done,"total":len(ordered),"last":int(time.time()),"errors":errs}
    threading.Thread(target=worker,daemon=True).start()


def _ensure_detail_background_jobs(race_id: str, detail: dict) -> None:
    if detail.get("date")!=_today_iso() or _snapshot_final(detail):return
    try:
        es=_enrichment_status(race_id)
        if es.get("status") in {"idle","unavailable"}:_start_enrichment(race_id,detail)
    except Exception as exc:
        print("prepared enrichment schedule failed",race_id,exc)
    try:
        if race_id.startswith("nar-"):
            names=[str(h.get("name") or "") for h in detail.get("horses",[]) if h.get("name")]
            cov=_history_counts(names,detail.get("date") or "9999-12-31")
            if _race_history_status(race_id) is None and not _history_is_enough(cov,0):_start_race_history_search(race_id,detail.get("date") or _today_iso(),names)
        else:
            cov=_central_detail_coverage(detail);total=int(cov.get("totalHorses") or 0);resolved=int(cov.get("horsesResolved") or cov.get("horsesWith5Plus") or 0)
            if detail.get("analysisMode")!="新馬" and _race_history_status(race_id) is None and not assess_career_readiness(detail).get("ready"):_start_central_history_search(race_id,detail.get("date") or _today_iso())
    except Exception as exc:
        print("prepared history schedule failed",race_id,exc)


def _schedule_detail_background_jobs(race_id: str, detail: dict) -> None:
    threading.Thread(target=_ensure_detail_background_jobs,args=(race_id,detail),daemon=True).start()


_racedb_refresh_lock=threading.Lock()
_racedb_refresh_running:set[str]=set()

def _fast_local_race_detail(race_id:str)->dict|None:
    return _acq_snapshots_local._fast_local_race_detail(
        race_id,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, DB_PATH=DB_PATH, RACEDB=RACEDB,
        _new_conn=_new_conn,
    )


def _build_fast_diagnosis_snapshot(race_id:str, allow_network:bool=False, deep_context:bool=False)->dict|None:
    """Recalculate all-horse diagnosis from local data only. Target: sub-second."""
    # Preserve current-card/result fields already hydrated by the fast-card step.
    # v156 rebuilt from the bare local NAR DB here and immediately erased body weights/results.
    detail=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if detail:
        detail=json.loads(json.dumps(detail,ensure_ascii=False,default=str))
    if not detail:return None
    if race_id.startswith("nar-"):
        detail=_nar_attach_recent_batch(detail,5)
    else:
        for h in detail.get("horses",[]) or []:
            h["recentRaces"]=list(h.get("recentRaces") or [])[:5]

    # Merge every locally stored historical start before computing diagnosis.
    detail=_attach_stored_career(detail)
    detail=_apply_enrichment(race_id,detail)

    quality=_diagnosis_history_quality(detail)
    if allow_network and not race_id.startswith("nar-") and not quality.get("ready") and detail.get("analysisMode")!="新馬":
        # Background/prewarm only: one page contains up to 5 previous starts for every runner.
        detail=_merge_fast_history(detail,_netkeiba_past_rows_fast(detail))
        detail=_attach_stored_career(detail)
        quality=_diagnosis_history_quality(detail)

    detail=_strip_excluded(detail)
    if deep_context:detail=_attach_evaluation_context(detail)
    detail=_precompute_detail_metrics(detail)
    detail=_restore_saved_odds(detail)
    quality=_diagnosis_history_quality(detail)

    pm=detail.setdefault("preparedMeta",{})
    pm.pop("fastPartial",None)
    pm["diagnosisVersion"]=PREDICTION_ENGINE_VERSION
    pm["diagnosisReady"]=bool(quality.get("ready"))
    pm["diagnosisPreparedAtEpoch"]=time.time()
    pm["diagnosisCoverage"]=quality
    detail["historySearch"]={
        "status":"local-ready" if quality.get("ready") else "history-loading",
        "monthsDone":0,"maxMonths":0,
        "coverage":{
            "totalHorses":quality.get("total",0),
            "totalRuns":quality.get("runs",0),
            "horsesWithHistory":quality.get("withHistory",0),
        },
        "error":"","source":"RaceDB + 一括5走履歴"
    }
    try:
        RACEDB.upsert_race(detail)
        _schedule_full_history_harvest(detail)
    except Exception as exc:print("fast diagnosis RaceDB save failed",race_id,exc)
    try:PREPARED_STORE.put(detail,force=True)
    except Exception as exc:print("fast diagnosis prepared save failed",race_id,exc)
    return _compact_display_snapshot(detail)


def _store_fast_snapshot(detail:dict)->None:
    if not detail or not _racedb_snapshot_usable(detail):return
    detail=_restore_saved_odds(detail)
    try:PREPARED_STORE.put(detail,force=True)
    except Exception as exc:print("fast prepared save failed",detail.get("id"),exc)
    try:RACEDB.upsert_race(detail)
    except Exception as exc:print("fast RaceDB save failed",detail.get("id"),exc)


_fast_card_lock=threading.Lock()
_fast_card_running:set[str]=set()
_fast_card_pending:set[str]=set()
_fast_card_queue=[]
_fast_card_cv=threading.Condition()
_fast_card_workers_started=False

def _ensure_fast_card_workers():
    global _fast_card_workers_started
    with _fast_card_cv:
        if _fast_card_workers_started:return
        _fast_card_workers_started=True
        workers=max(1,min(6,int(os.getenv("FAST_CARD_WORKERS","4"))))
        for idx in range(workers):
            threading.Thread(target=_fast_card_worker,daemon=True,name=f"fast-card-worker-{idx+1}").start()

def _queue_fast_card(race_id:str,priority:int=50):
    if not race_id:return
    _ensure_fast_card_workers()
    with _fast_card_cv:
        if race_id in _fast_card_pending or race_id in _fast_card_running:return
        _fast_card_pending.add(race_id)
        _fast_card_queue.append((int(priority),time.time(),race_id))
        _fast_card_queue.sort(key=lambda x:(x[0],x[1]))
        _fast_card_cv.notify()

def _fast_card_worker():
    while True:
        with _fast_card_cv:
            while not _fast_card_queue:_fast_card_cv.wait()
            priority,_,race_id=_fast_card_queue.pop(0)
            _fast_card_pending.discard(race_id)
            _fast_card_running.add(race_id)
        try:
            deep=priority<=10
            _hydrate_fast_card_now(race_id,deep_history=deep)
            try:_build_fast_diagnosis_snapshot(race_id,allow_network=False,deep_context=deep)
            except Exception as exc:print("fast diagnosis after card failed",race_id,exc)
        except Exception as exc:
            print("fast card worker failed",race_id,exc)
        finally:
            with _fast_card_cv:_fast_card_running.discard(race_id)

def _parse_nar_official_card_html(detail:dict, html:str)->list[dict]:
    return _acq_local_racecards._parse_nar_official_card_html(
        detail, html,
    )


def _nar_official_card_rows_fast(detail:dict)->list[dict]:
    return _acq_local_racecards._nar_official_card_rows_fast(
        detail,
        _parse_nar_official_card_html=_parse_nar_official_card_html,
    )


def _merge_current_card_fields(detail:dict, rows:list[dict])->dict:
    return _acq_merge_current._merge_current_card_fields(
        detail, rows,
        _now_jst=_now_jst,
    )


def _nar_result_should_be_available(detail:dict, grace_min:int=1)->bool:
    return _acq_local_results._nar_result_should_be_available(
        detail, grace_min,
        _now_jst=_now_jst, _today_iso=_today_iso,
    )


def _nar_official_result_fast(detail:dict)->dict|None:
    return _acq_local_results._nar_official_result_fast(
        detail,
        _env_clean_condition=_env_clean_condition, _env_clean_weather=_env_clean_weather,
    )


def _netkeiba_card_rows_fast(detail:dict)->list[dict]:
    return _acq_netkeiba_racecards._netkeiba_card_rows_fast(
        detail,
        _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id, _nk_row_horse=_nk_row_horse,
    )


def _netkeiba_past_rows_fast(detail:dict)->list[dict]:
    return _acq_netkeiba_history._netkeiba_past_rows_fast(
        detail,
        _netkeiba_get=_netkeiba_get, _netkeiba_race_id=_netkeiba_race_id, _nk_row_horse=_nk_row_horse,
    )


def _hydrate_fast_card_now(race_id:str, deep_history:bool=False)->None:
    # NAR: hydrate the date once. v117 called a non-existent sync_day(), so selected
    # local races could stay empty until another background job happened to fill the DB.
    return _acq_snapshots_hydration._hydrate_fast_card_now(
        race_id, deep_history,
        CENTRAL_DB_PATH=CENTRAL_DB_PATH, CentralStore=CentralStore, NarSync=NarSync,
        RACEDB=RACEDB, _fast_local_race_detail=_fast_local_race_detail, _history_counts=_history_counts,
        _jra_fetch_environment=_jra_fetch_environment, _jra_find_cname=_jra_find_cname, _jra_parse_race=_jra_parse_race,
        _merge_current_card_fields=_merge_current_card_fields, _merge_result_fields=_merge_result_fields, _nar_official_card_rows_fast=_nar_official_card_rows_fast,
        _nar_official_result_fast=_nar_official_result_fast, _nar_result_should_be_available=_nar_result_should_be_available, _netkeiba_card_rows_fast=_netkeiba_card_rows_fast,
        _netkeiba_past_rows_fast=_netkeiba_past_rows_fast, _new_conn=_new_conn, _now_jst=_now_jst,
        _start_race_history_search=_start_race_history_search, _store_fast_snapshot=_store_fast_snapshot, _today_iso=_today_iso,
    )

def _schedule_fast_card_refresh(race_id:str,priority:int=50)->None:
    _queue_fast_card(race_id,priority)


def _schedule_racedb_snapshot_refresh(race_id:str)->None:
    with _racedb_refresh_lock:
        if race_id in _racedb_refresh_running:return
        _racedb_refresh_running.add(race_id)
    def worker():
        try:
            fresh=_prepare_race_snapshot(race_id,True)
            if fresh:_ensure_detail_background_jobs(race_id,fresh)
        except Exception as exc:print("RaceDB refresh failed",race_id,exc)
        finally:
            with _racedb_refresh_lock:_racedb_refresh_running.discard(race_id)
    threading.Thread(target=worker,daemon=True).start()

def _racedb_get_fast(race_id:str)->dict|None:
    try:detail,updated=RACEDB.get_race(race_id)
    except Exception:return None
    if not detail or not _racedb_snapshot_usable(detail):return None
    if (detail.get("preparedMeta") or {}).get("fastPartial"):return detail
    if (detail.get("aiEvaluation") or {}).get("version")!=AI_EVALUATION_VERSION:
        detail=_precompute_detail_metrics(_strip_excluded(detail))
    detail=_ensure_race_volatility(detail)
    detail=_restore_saved_odds(detail)
    return detail

_detail_cache_lock=threading.Lock()
_detail_cache:dict[str,tuple[float,dict]]={}

_race_list_cache_lock = threading.Lock()
_race_list_cache: dict[str, tuple[float, list[dict]]] = {}


def _local_starter_bundle(rows:list[dict], limit:int=3)->list[dict]:
    if not rows:return []
    ordered=sorted(
        [r for r in rows if r.get("id")],
        key=lambda r:(str(r.get("track") or ""),int(r.get("raceNumber") or 0))
    )
    first_track=str(ordered[0].get("track") or "") if ordered else ""
    candidates=[r for r in ordered if str(r.get("track") or "")==first_track][:limit]
    out=[]
    for r in candidates:
        rid=str(r.get("id") or "")
        d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        if d and (d.get("horses") or []):
            out.append(_compact_display_snapshot(d))
    return out


_volatility_pack_lock=threading.Lock()
_volatility_pack_cache:dict[str,tuple[float,list[dict]]]={}

def _local_volatility_map(race_ids:list[str])->dict[str,dict]:
    ids=[str(x) for x in race_ids if x]
    if not ids:return {}
    out={}
    # PreparedStore first.
    if PREPARED_DB_PATH.exists():
        conn=sqlite3.connect(PREPARED_DB_PATH,timeout=.25)
        conn.row_factory=sqlite3.Row
        try:
            for start in range(0,len(ids),200):
                chunk=ids[start:start+200]
                ph=",".join("?" for _ in chunk)
                rows=conn.execute(
                    f"SELECT race_id,payload FROM prepared_races WHERE race_id IN ({ph})",
                    chunk
                ).fetchall()
                for row in rows:
                    try:d=json.loads(row["payload"])
                    except Exception:continue
                    d=_ensure_race_volatility(d)
                    v=d.get("volatility") or {}
                    if v.get("version")==VOLATILITY_ENGINE_VERSION:
                        out[str(row["race_id"])]=v
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    missing=[rid for rid in ids if rid not in out]
    if missing and RACEDB_PATH.exists():
        conn=sqlite3.connect(RACEDB_PATH,timeout=.25)
        conn.row_factory=sqlite3.Row
        try:
            for start in range(0,len(missing),200):
                chunk=missing[start:start+200]
                ph=",".join("?" for _ in chunk)
                rows=conn.execute(
                    f"SELECT race_id,payload FROM race_snapshots WHERE race_id IN ({ph})",
                    chunk
                ).fetchall()
                for row in rows:
                    try:d=json.loads(row["payload"])
                    except Exception:continue
                    d=_ensure_race_volatility(d)
                    v=d.get("volatility") or {}
                    if v.get("version")==VOLATILITY_ENGINE_VERSION:
                        out[str(row["race_id"])]=v
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    return out


def _attach_local_volatility_to_summaries(rows:list[dict])->list[dict]:
    if not rows:return rows
    vm=_local_volatility_map([str(r.get("id") or "") for r in rows])
    if not vm:return rows
    out=[]
    for r in rows:
        z=dict(r)
        v=vm.get(str(z.get("id") or ""))
        if v:z["volatility"]=v
        out.append(z)
    return out


def _compute_local_volatility_for_race(race_id:str)->dict|None:
    # Strictly local: no public-site wait. Used by the selected venue's 12-row pack.
    d=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if d:
        d=_ensure_race_volatility(d)
        v=d.get("volatility") or {}
        if v.get("ready"):return v

    d=_fast_local_race_detail(race_id)
    if not d:return v if 'v' in locals() and v else None
    try:
        if race_id.startswith("nar-"):d=_nar_attach_recent_batch(d,5)
        d=_attach_stored_career(d)
        d=_precompute_detail_metrics(d)
        v=d.get("volatility") or {}
        # Save so the next page/open is zero-wait.
        try:
            PREPARED_STORE.put(d,force=True)
            RACEDB.upsert_race(d)
        except Exception:
            pass
        return v if v.get("version")==VOLATILITY_ENGINE_VERSION else None
    except Exception as exc:
        print("local volatility compute failed",race_id,exc)
        return None


@app.get("/api/v1/volatility-pack")
def volatility_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...)):
    """All 1R-12R upset labels from local DB only. Designed for sub-second venue paint."""
    key=f"{date}|{circuit}|{track}"
    now=time.time()
    with _volatility_pack_lock:
        hit=_volatility_pack_cache.get(key)
        if hit and now-hit[0]<8:
            return {"date":date,"circuit":circuit,"track":track,"races":hit[1],"cached":True}

    try:
        summaries=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
    except Exception:
        summaries=[]
    targets=[r for r in summaries if str(r.get("track") or "")==str(track) and r.get("id")]
    targets.sort(key=lambda r:int(r.get("raceNumber") or 0))

    existing=_local_volatility_map([str(r.get("id") or "") for r in targets])
    items=[]
    for r in targets:
        rid=str(r.get("id") or "")
        v=existing.get(rid)
        if not v or not v.get("ready"):
            v=_compute_local_volatility_for_race(rid) or v
        items.append({
            "id":rid,
            "raceNumber":int(r.get("raceNumber") or 0),
            "volatility":v or {
                "version":VOLATILITY_ENGINE_VERSION,"ready":False,
                "score":None,"label":"…","method":"pre-race/no-odds",
                "oddsUsed":False,"reasons":["評価材料を収集中"]
            }
        })

    with _volatility_pack_lock:
        _volatility_pack_cache[key]=(now,items)
        if len(_volatility_pack_cache)>40:
            oldest=min(_volatility_pack_cache.items(),key=lambda kv:kv[1][0])[0]
            _volatility_pack_cache.pop(oldest,None)
    return {"date":date,"circuit":circuit,"track":track,"races":items,"cached":False}


@app.get("/api/v1/races")
def races(date: str = Query(...), circuit: str = Query(""), force: int = Query(0), bundle: int = Query(0)):
    circuit=_clean(circuit)
    now=time.time();ck=f"{date}|{circuit or 'all'}"
    with _race_list_cache_lock:
        hit=_race_list_cache.get(ck)
        if hit and not force and ((hit[1] and date<_today_iso()) or now-hit[0]<15):
            cached_rows=_attach_local_volatility_to_summaries(hit[1] or [])
            if circuit:
                return {"races":cached_rows,"prepared":_local_starter_bundle(cached_rows)} if bundle else cached_rows
            has_central=any(str(x.get("circuit") or "")=="中央" for x in cached_rows)
            has_local=any(str(x.get("circuit") or "")=="地方" for x in cached_rows)
            if date<_today_iso() or (has_central and has_local):
                return {"races":cached_rows,"prepared":_local_starter_bundle(cached_rows)} if bundle else cached_rows
        if force:_race_list_cache.pop(ck,None)
    rows=[]
    if circuit in ("","地方"):
        try:
            nar_rows=nar_race_summaries(date)
        except Exception as exc:
            print(f"NAR summary read failed: {exc}");nar_rows=[]
        rows.extend(nar_rows)
        if force or not nar_rows:_schedule_live_refresh(date, force=bool(force))
    if circuit in ("","中央"):
        try:
            crows=central_race_summaries(date,allow_network=False,force=False)
        except Exception as exc:
            print(f"Central summary read failed: {exc}");crows=[]
        rows.extend(crows)
        if force or not crows:_schedule_central_refresh(date,force=bool(force))
    rows=[x for x in rows if str(x.get("track") or "")!="帯広"]
    rows=_attach_local_volatility_to_summaries(rows)
    if date==_today_iso():
        for circuit_name in ("中央","地方"):
            for track_name in sorted({str(x.get("track") or "") for x in rows if str(x.get("circuit") or "")==circuit_name}):
                if not track_name:continue
                subset=[x for x in rows if str(x.get("circuit") or "")==circuit_name and str(x.get("track") or "")==track_name]
                if any(str(x.get("weather") or "不明")=="不明" or str(x.get("condition") or "不明")=="不明" for x in subset):
                    _schedule_track_environment(date,circuit_name,track_name,False)
    with _race_list_cache_lock:
        _race_list_cache[ck]=(now,rows)
        if len(_race_list_cache)>24:
            oldest=min(_race_list_cache.items(),key=lambda kv:kv[1][0])[0];_race_list_cache.pop(oldest,None)
    return {"races":rows,"prepared":_local_starter_bundle(rows)} if bundle else rows


@app.get("/api/v1/environment-pack")
def environment_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...)):
    rows=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
    rows=[r for r in rows if str(r.get("track") or "")==str(track)]
    out=[{
        "id":str(r.get("id") or ""),
        "raceNumber":int(r.get("raceNumber") or 0),
        "weather":str(r.get("weather") or "不明"),
        "condition":str(r.get("condition") or "不明"),
        "environmentMeta":r.get("environmentMeta") or {},
    } for r in rows if r.get("id")]
    # If today's environment is still missing, start background refresh but return immediately.
    if date==_today_iso() and any(x["weather"]=="不明" or x["condition"]=="不明" for x in out):
        _schedule_track_environment(date,circuit,track,False)
    return {"date":date,"circuit":circuit,"track":track,"races":out,"count":len(out),"source":"local-only"}


@app.get("/api/v1/track-pack")
def track_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...), fill: int = Query(1)):
    """Return venue snapshots from local DB only; fill local-only gaps for instant taps."""
    out=[]
    seen=set()

    # Prepared store first.
    if PREPARED_DB_PATH.exists():
        conn=sqlite3.connect(PREPARED_DB_PATH,timeout=.35)
        conn.row_factory=sqlite3.Row
        try:
            rows=conn.execute(
                "SELECT race_id,payload FROM prepared_races WHERE race_date=? AND circuit=? ORDER BY race_id",
                (date,circuit),
            ).fetchall()
            for row in rows:
                try:d=json.loads(row["payload"])
                except Exception:continue
                if str(d.get("track") or "")!=track:continue
                if not (d.get("horses") or []):continue
                rid=str(d.get("id") or row["race_id"] or "")
                if not rid or rid in seen:continue
                d=_restore_saved_odds(_ensure_race_volatility(d));seen.add(rid);out.append(_compact_display_snapshot(d))
        finally:
            conn.close()

    # RaceDB fills any gaps without network access.
    if RACEDB_PATH.exists():
        conn=sqlite3.connect(RACEDB_PATH,timeout=.35)
        conn.row_factory=sqlite3.Row
        try:
            rows=conn.execute(
                "SELECT race_id,payload FROM race_snapshots WHERE race_date=? AND circuit=? AND track=? ORDER BY race_no",
                (date,circuit,track),
            ).fetchall()
            for row in rows:
                rid=str(row["race_id"] or "")
                if not rid or rid in seen:continue
                try:d=json.loads(row["payload"])
                except Exception:continue
                if not (d.get("horses") or []):continue
                d=_restore_saved_odds(_ensure_race_volatility(d));seen.add(rid);out.append(_compact_display_snapshot(d))
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    # Fill missing races from local stores only. This path never waits on public sites.
    if fill:
        try:
            summaries=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
        except Exception:
            summaries=[]
        targets=[r for r in summaries if str(r.get("track") or "")==str(track) and r.get("id")]
        missing=[str(r.get("id") or "") for r in targets if str(r.get("id") or "") not in seen]
        def build_local(rid):
            try:
                d=_fast_local_race_detail(rid)
                if not d:
                    _schedule_fast_card_refresh(rid,25)
                    return None
                d=_restore_saved_odds(d)
                d=_ensure_race_volatility(d)
                return _compact_display_snapshot(d)
            except Exception as exc:
                print("track-pack local fill failed",rid,exc)
                return None
        workers=max(1,min(4,len(missing))) if missing else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for d in pool.map(build_local,missing):
                    if d and d.get("id"):
                        rid=str(d.get("id"))
                        if rid not in seen:
                            seen.add(rid)
                            out.append(d)
                            _schedule_fast_card_refresh(rid,35+int(d.get("raceNumber") or 0))
    out.sort(key=lambda d:int(d.get("raceNumber") or 0))
    return {"track":track,"date":date,"circuit":circuit,"races":out,"count":len(out),"source":"local-only","filled":bool(fill)}


_site_bootstrap_lock=threading.Lock()
_site_bootstrap_build_lock=threading.Lock()
_site_bootstrap_cache:dict[str,tuple[float,dict]]={}
_site_force_cache:dict[str,tuple[float,dict]]={}
_site_bootstrap_state:dict[str,dict]={}

class DayBundleStore:
    def __init__(self,path:Path):
        self.path=path
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS day_bundles(
                race_date TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                complete INTEGER NOT NULL DEFAULT 0,
                race_count INTEGER NOT NULL DEFAULT 0,
                detail_count INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            )""")
            conn.commit()
        finally:conn.close()

    def get(self,race_date:str,complete_only:bool=False)->dict|None:
        conn=sqlite3.connect(self.path,timeout=3);conn.row_factory=sqlite3.Row
        try:
            sql="SELECT * FROM day_bundles WHERE race_date=?"
            args=[race_date]
            if complete_only:sql+=" AND complete=1"
            row=conn.execute(sql,args).fetchone()
            if not row:return None
            try:p=json.loads(row["payload"])
            except Exception:return None
            p["persisted"]=True
            p["updatedAtEpoch"]=int(row["updated_at"] or 0)
            p["complete"]=bool(row["complete"])
            p["raceCount"]=int(row["race_count"] or 0)
            p["detailCount"]=int(row["detail_count"] or 0)
            return p
        finally:conn.close()

    def put(self,race_date:str,payload:dict,complete:bool)->None:
        if not race_date or not isinstance(payload,dict):return
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""INSERT INTO day_bundles(race_date,payload,complete,race_count,detail_count,updated_at)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(race_date) DO UPDATE SET
                              payload=excluded.payload,complete=excluded.complete,
                              race_count=excluded.race_count,detail_count=excluded.detail_count,
                              updated_at=excluded.updated_at""",
                         (race_date,json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str),
                          1 if complete else 0,int(payload.get("raceCount") or 0),
                          int(payload.get("detailCount") or 0),int(time.time())))
            conn.commit()
        finally:conn.close()

DAY_BUNDLES=DayBundleStore(DAY_BUNDLE_DB_PATH)

def _bootstrap_rows_local(date:str)->list[dict]:
    raw=races(date,"",0,0)
    rows=raw.get("races",[]) if isinstance(raw,dict) else list(raw or [])
    out=[];seen=set()
    for r in rows:
        rid=str(r.get("id") or "")
        if not rid or rid in seen:continue
        seen.add(rid);out.append(r)
    out.sort(key=lambda r:(str(r.get("circuit") or ""),str(r.get("track") or ""),int(r.get("raceNumber") or 0)))
    return out

def _bootstrap_sources_running(date:str)->bool:
    running=False
    try:
        with _live_refresh_lock:
            running=running or (f"live:{date}" in _live_refresh_running)
    except Exception:pass
    try:
        running=running or bool(_central_refresh_status(date).get("running"))
    except Exception:pass
    return bool(running)


def _bootstrap_analysis_ready(d:dict|None)->bool:
    """Diagnosis readiness is tracked separately and must never block site display."""
    if not _bootstrap_display_ready(d):return False
    if _snapshot_final(d):return True
    pm=d.get("preparedMeta") or {}
    return bool(pm.get("diagnosisReady") and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION)

# Compatibility for older internal callers: "ready" now means display-ready.

def _bootstrap_detail_local(race_id:str,force_hydrate:bool=False)->dict|None:
    """Fast local snapshot for day bundles. Heavy diagnosis work is background-only."""
    d=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if not d:
        try:d=_fast_local_race_detail(race_id)
        except Exception:d=None
    if not d:
        if force_hydrate:_schedule_fast_card_refresh(race_id,5)
        return None
    d=_restore_saved_odds(d)
    d=_ensure_race_volatility(d)
    if force_hydrate and not _bootstrap_analysis_ready(d):_schedule_fast_card_refresh(race_id,8)
    return _compact_display_snapshot(d)

def _assemble_day_bundle(date:str,allow_network_fill:bool=False)->dict:
    rows=_bootstrap_rows_local(date)
    details=[]
    if rows:
        workers=max(1,min(8,int(os.getenv("DAY_BUNDLE_WORKERS","6")),len(rows)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={
                pool.submit(_bootstrap_detail_local,str(r.get("id")),allow_network_fill):str(r.get("id"))
                for r in rows
            }
            for fut in as_completed(futures):
                try:d=fut.result()
                except Exception as exc:
                    print("day bundle race failed",futures[fut],exc);d=None
                if d and d.get("id"):details.append(d)

    details.sort(key=lambda d:(str(d.get("circuit") or ""),str(d.get("track") or ""),int(d.get("raceNumber") or 0)))
    display_ids={str(d.get("id") or "") for d in details if _bootstrap_display_ready(d)}
    analysis_ids={str(d.get("id") or "") for d in details if _bootstrap_analysis_ready(d)}
    missing=[str(r.get("id") or "") for r in rows if str(r.get("id") or "") not in display_ids]
    source_running=_bootstrap_sources_running(date)
    display_complete=bool(rows) and not missing and not source_running

    return {
        "date":date,"races":rows,"details":details,
        "raceCount":len(rows),"detailCount":len(display_ids),
        "analysisCount":len(analysis_ids),
        "missing":missing,
        "complete":display_complete,
        "displayComplete":display_complete,
        "analysisComplete":bool(rows) and len(analysis_ids)>=len(rows),
        "sourceRunning":source_running,
        "generatedAtEpoch":int(time.time()),
        "source":"nonblocking-day-bundle"
    }

def _refresh_day_bundle(date:str,force_sources:bool=False,wait_for_complete:bool=False,timeout_sec:float=25.0)->dict:
    """Single-pass bundle refresh. Missing/outdated races are queued and never block the caller."""
    started=time.time()
    with _site_bootstrap_build_lock:
        with _site_bootstrap_lock:
            _site_bootstrap_state[date]={"running":True,"startedAt":int(started),"raceCount":0,"ready":0,"missing":[]}
        if force_sources or date==_today_iso():
            try:_schedule_live_refresh(date,force=bool(force_sources))
            except Exception:pass
            try:_schedule_central_refresh(date,force=bool(force_sources))
            except Exception:pass
        payload=_assemble_day_bundle(date,allow_network_fill=False)
        missing=list(payload.get("missing") or [])
        for rid in missing:_schedule_fast_card_refresh(rid,5)
        for d in payload.get("details") or []:
            if d and d.get("id") and not _bootstrap_analysis_ready(d):_schedule_fast_card_refresh(str(d.get("id")),12)
        try:DAY_BUNDLES.put(date,payload,bool(payload.get("displayComplete")))
        except Exception:pass
        with _site_bootstrap_lock:
            _site_bootstrap_cache[date]=(time.time(),payload)
            _site_bootstrap_state[date]={
                "running":False,"startedAt":int(started),"finishedAt":int(time.time()),
                "raceCount":int(payload.get("raceCount") or 0),"ready":int(payload.get("detailCount") or 0),
                "analysisReady":int(payload.get("analysisCount") or 0),"missing":missing,
                "sourceRunning":bool(payload.get("sourceRunning")),"elapsedMs":int((time.time()-started)*1000),
            }
        return payload

def _schedule_day_bundle_refresh(date:str,force_sources:bool=False)->None:
    with _site_bootstrap_lock:
        st=_site_bootstrap_state.get(date) or {}
        if st.get("running"):return
        _site_bootstrap_state[date]={"running":True,"startedAt":int(time.time()),"raceCount":0,"ready":0,"missing":[]}
    def worker():
        try:_refresh_day_bundle(date,force_sources,True,float(os.getenv("DAY_BUNDLE_BUILD_TIMEOUT_SEC","45")))
        except Exception as exc:
            print("day bundle refresh failed",date,exc)
            with _site_bootstrap_lock:
                st=dict(_site_bootstrap_state.get(date) or {})
                st.update({"running":False,"error":str(exc),"finishedAt":int(time.time())})
                _site_bootstrap_state[date]=st
    threading.Thread(target=worker,daemon=True,name="day-bundle-"+date).start()

def _site_bootstrap_payload(date:str,force:bool=False,wait:bool=False)->dict:
    """
    Customer path is strictly non-blocking.
    Return the best local bundle immediately, then continue full preparation in background.
    v240: a fresh force=1 collector result must not be immediately replaced by an
    older persisted bundle on the next non-force poll.
    """
    stored=DAY_BUNDLES.get(date,complete_only=True)
    recent_force=None
    with _site_bootstrap_lock:
        fc=_site_force_cache.get(date)
        if fc and time.time()-float(fc[0])<=60:
            recent_force=dict(fc[1])
    if not force and recent_force and (not stored or _bundle_quality(recent_force)>=_bundle_quality(stored)):
        out=dict(recent_force)
        out["cached"]=False
        out["servedFrom"]="recent-force-live"
        return out
    if stored and not force:
        if date==_today_iso() and int(time.time())-int(stored.get("updatedAtEpoch") or 0)>20:
            _schedule_day_bundle_refresh(date,False)
        out=dict(stored)
        out["cached"]=True
        out["servedFrom"]="persistent-display-complete"
        return out

    # Local-only assembly: no external fetch and no waiting for the builder lock.
    try:
        current=_assemble_day_bundle(date,allow_network_fill=False)
    except Exception as exc:
        print("nonblocking bootstrap assemble failed",date,exc)
        current={"date":date,"races":[],"details":[],"raceCount":0,"detailCount":0,
                 "analysisCount":0,"missing":[],"complete":False,
                 "displayComplete":False,"analysisComplete":False,
                 "sourceRunning":False,"generatedAtEpoch":int(time.time()),
                 "source":"nonblocking-day-bundle"}

    # Persist a complete display bundle; analysis may still improve later.
    if current.get("displayComplete"):
        try:DAY_BUNDLES.put(date,current,True)
        except Exception:pass

    # Always kick the expensive work into background.
    _schedule_day_bundle_refresh(date,bool(force))

    current["cached"]=False
    current["servedFrom"]="local-immediate"
    return current

def _force_day_live_snapshot(date:str, timeout_sec:float=23.0)->dict:
    """GitHub collector path: all-card live fields first, diagnosis second.

    v304 refreshed each race as one long job (card -> odds -> result -> diagnosis).
    Slow diagnosis jobs could occupy all workers and starve later races before their
    odds call ever started.  v305 splits the phases: every race gets an odds attempt
    first; only then do we spend the remaining budget on results/diagnosis.
    """
    started=time.time()
    try:_schedule_live_refresh(date,force=True)
    except Exception:pass
    try:_schedule_central_refresh(date,force=True)
    except Exception:pass
    deadline=started+max(8.0,float(timeout_sec))
    # Let program/card discovery start, but reserve most of the request for market data.
    while time.time()<deadline and _bootstrap_sources_running(date):
        if time.time()-started>2.2:break
        time.sleep(.15)
    rows=_bootstrap_rows_local(date)
    if not rows:
        return _site_bootstrap_payload(date,True,False)

    def snapshot(rid:str)->dict:
        return _prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid) or {}

    def live_coverage(d:dict)->tuple[int,int,int]:
        hs=[h for h in (d.get("horses") or []) if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
        got=sum(1 for h in hs if float(h.get("winOdds") or 0)>0)
        weights=sum(1 for h in hs if int(h.get("bodyWeight") or 0)>250)
        return len(hs),got,weights

    # PHASE 1 — FULL CARD ODDS. No diagnosis is allowed to block these workers.
    def market_one(row):
        rid=str(row.get("id") or "")
        if not rid:return rid,False
        try:
            d=snapshot(rid)
            if not _bootstrap_display_ready(d):
                try:_hydrate_fast_card_now(rid,deep_history=False)
                except Exception as exc:print("full-day card hydrate failed",rid,exc)
            body=odds_refresh(rid,1)
            field=int((body or {}).get("fieldCount") or 0);got=int((body or {}).get("oddsCount") or 0)
            return rid,bool(field and got==field)
        except Exception as exc:
            print("full-day market refresh failed",rid,exc)
            return rid,False

    market_workers=max(6,min(int(os.getenv("FULL_DAY_ODDS_WORKERS","20")),24,len(rows)))
    market_results={}
    ex=ThreadPoolExecutor(max_workers=market_workers)
    futures={ex.submit(market_one,r):str(r.get("id") or "") for r in rows}
    # Reserve a few seconds for a second sparse-row pass and bundle assembly.
    market_deadline=min(deadline-5.0,time.time()+max(6.0,min(14.0,deadline-time.time()-5.0)))
    try:
        done,_=wait(list(futures),timeout=max(.5,market_deadline-time.time()))
        for fut in done:
            rid=futures[fut]
            try:market_results[rid]=bool(fut.result()[1])
            except Exception:market_results[rid]=False
    finally:
        ex.shutdown(wait=False,cancel_futures=True)

    # PHASE 1B — retry only races still missing at least one active runner's odds.
    missing=[]
    for r in rows:
        rid=str(r.get("id") or "")
        field,got,_=live_coverage(snapshot(rid))
        if rid and field and got<field:missing.append(r)
    if missing and time.time()<deadline-2.5:
        retry_workers=max(4,min(int(os.getenv("FULL_DAY_ODDS_RETRY_WORKERS","16")),20,len(missing)))
        ex=ThreadPoolExecutor(max_workers=retry_workers)
        fs=[ex.submit(market_one,r) for r in missing]
        try:wait(fs,timeout=max(.5,min(4.0,deadline-time.time()-2.0)))
        finally:ex.shutdown(wait=False,cancel_futures=True)

    # PHASE 2 — results and body-weight-sensitive diagnosis only for the useful time window.
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    focus=[]
    for r in rows:
        st=_race_minutes_server(r)
        remain=(st-nowm) if st<9999 else 9999
        if (-45<=remain<=240) or not _bootstrap_analysis_ready(snapshot(str(r.get("id") or ""))):
            focus.append(r)
    focus.sort(key=lambda r:abs((_race_minutes_server(r) if _race_minutes_server(r)<9999 else nowm+9999)-nowm))
    focus=focus[:max(12,min(28,len(focus)))]

    def finish_one(row):
        rid=str(row.get("id") or "")
        if not rid:return None
        try:
            st=_race_minutes_server(row)
            if st<9999 and nowm>=st+2 and not _snapshot_final(snapshot(rid)):
                try:_refresh_result_fast(rid)
                except Exception:pass
            # Rebuild only after live fields have been persisted, so newly published
            # body weight can affect the current diagnosis without starving market fetches.
            try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
            except Exception as exc:print("focused diagnosis rebuild failed",rid,exc)
            d=snapshot(rid)
            return _compact_display_snapshot(d) if d else None
        except Exception as exc:
            print("focused live rebuild failed",rid,exc)
            return None

    if focus and time.time()<deadline-1.2:
        workers=max(4,min(10,len(focus)))
        ex=ThreadPoolExecutor(max_workers=workers)
        fs=[ex.submit(finish_one,r) for r in focus]
        try:wait(fs,timeout=max(.4,deadline-time.time()-1.0))
        finally:ex.shutdown(wait=False,cancel_futures=True)

    out=_assemble_day_bundle(date,allow_network_fill=False)
    if out.get("displayComplete"):
        try:DAY_BUNDLES.put(date,out,True)
        except Exception:pass
    dc_ready=0
    for d in out.get("details",[]) or []:
        try:
            hh=_data_core_store_health(d,set(),"force-day")
            if all((hh.get(k) or {}).get("status")=="ready" for k in ("card","history","odds","body_weight","environment","analysis")):
                dc_ready+=1
        except Exception as exc:print("data core force health failed",(d or {}).get("id"),exc)
    out["dataCore"]={"version":ARVEXQ_DATA_CORE_VERSION,"readyRaceCount":dc_ready,"raceCount":len(out.get("races") or [])}
    odds_ready=0;odds_partial=0;odds_missing=[]
    for d in out.get("details",[]) or []:
        hs=[h for h in (d.get("horses") or []) if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
        got=sum(1 for h in hs if float(h.get("winOdds") or 0)>0)
        if hs and got==len(hs):odds_ready+=1
        elif hs and got:odds_partial+=1;odds_missing.append(str(d.get("id") or ""))
        elif hs:odds_missing.append(str(d.get("id") or ""))
    out["oddsReadyCount"]=odds_ready
    out["oddsPartialCount"]=odds_partial
    out["oddsMissingRaceIds"]=odds_missing
    out["forceLiveRefresh"]=True
    out["forceElapsedMs"]=int((time.time()-started)*1000)
    with _site_bootstrap_lock:
        _site_force_cache[date]=(time.time(),dict(out))
        _site_bootstrap_cache[date]=(time.time(),dict(out))
    return out

@app.get("/api/v1/site-bootstrap")
def site_bootstrap(date: str = Query(...), force: int = Query(0), wait: int = Query(0)):
    """Fast customer bootstrap; force=1 is the GitHub full-day collector path."""
    if force:
        try:return _force_day_live_snapshot(date,23.0)
        except Exception as exc:
            print("force day snapshot failed",date,exc)
    return _site_bootstrap_payload(date,False,False)

def _site_bootstrap_warm_loop():
    time.sleep(float(os.getenv("BOOTSTRAP_START_DELAY_SEC","2.5")))
    while True:
        try:_schedule_day_bundle_refresh(_today_iso(),False)
        except Exception as exc:print("bundle warmer failed",exc)
        time.sleep(max(20,int(os.getenv("BOOTSTRAP_REFRESH_SEC","30"))))

@app.on_event("startup")
def _start_site_bootstrap_warmer():
    enabled=str(os.getenv("ARVEXQ_BOOTSTRAP_WARM","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_site_bootstrap_warm_loop,daemon=True,name="arvexq-bootstrap").start()


@app.get("/api/v1/site-bootstrap-status")
def site_bootstrap_status(date: str = Query(...)):
    with _site_bootstrap_lock:state=dict(_site_bootstrap_state.get(date) or {})
    stored=DAY_BUNDLES.get(date,complete_only=True)
    state["persistedComplete"]=bool(stored)
    state["persistedUpdatedAt"]=int((stored or {}).get("updatedAtEpoch") or 0)
    return state


@app.get("/api/v1/past-pack/{race_id}")
def past_pack(race_id:str):
    """Return locally available recent-race snapshots only; zero public web calls."""
    current=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not current:return {"raceId":race_id,"races":[]}
    ids=[];seen=set()
    for h in current.get("horses",[]) or []:
        for rr in (h.get("recentRaces") or [])[:5]:
            rid=str(rr.get("raceId") or "")
            if not rid and str(current.get("circuit") or "")=="地方" and rr.get("date") and rr.get("track") and int(rr.get("raceNumber") or 0):
                rid=f"nar-{rr['date']}-{rr['track']}-{int(rr['raceNumber']):02d}"
            if rid and rid not in seen:
                seen.add(rid);ids.append(rid)
            if len(ids)>=18:break
        if len(ids)>=18:break
    out=[]
    for rid in ids:
        d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        if d and (d.get("horses") or d.get("result")):out.append(_compact_display_snapshot(d))
    return {"raceId":race_id,"races":out,"count":len(out),"source":"local-only"}


@app.post("/api/v1/prepare-race/{race_id}")
def prepare_race(race_id:str):
    """Queue the selected race first; customer HTTP request returns immediately."""
    _schedule_fast_card_refresh(race_id,0)
    return {"status":"queued","raceId":race_id,"priority":0}


@app.post("/api/v1/prewarm-track")
def prewarm_track(date: str = Query(...), circuit: str = Query(...), track: str = Query(...), race_no: int = Query(1)):
    rows=[]
    try:rows=(nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False))
    except Exception:rows=[]
    all_targets=sorted(
        [r for r in rows if str(r.get("track") or "")==str(track) and r.get("id")],
        key=lambda r:abs(int(r.get("raceNumber") or 0)-int(race_no))
    )
    near=all_targets[:3];rest=all_targets[3:]
    queued=0
    for idx,r in enumerate(near+rest):
        rid=str(r["id"])
        local=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        pm=(local or {}).get("preparedMeta") or {}
        v=(local or {}).get("volatility") or {}
        current=pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady") and v.get("version")==VOLATILITY_ENGINE_VERSION
        if not local or not current:
            priority=(10+idx*10) if idx<3 else (90+idx)
            _schedule_fast_card_refresh(rid,priority);queued+=1
    return {"status":"started","count":len(all_targets),"queued":queued,"mode":"nearest-3-plus-background"}


@app.get("/api/v1/local-refresh-status")
def local_refresh_status(date: str = Query(...)):
    key=f"live:{date}"
    with _live_refresh_lock:
        running=key in _live_refresh_running
        last=_live_refresh_last.get(key,0)
    try:
        count=len(nar_race_summaries(date))
    except Exception:
        count=0
    return {"running":running,"last":last,"count":count}

@app.get("/api/v1/central-refresh-status")
def central_refresh_status(date: str = Query(...)):
    st=_central_refresh_status(date)
    try: st["count"]=len(central_race_summaries(date,allow_network=False))
    except Exception: st["count"]=0
    return st

@app.get("/api/v1/race/{race_id}")
def race_detail(race_id: str, refresh: int = Query(0), history: int = Query(1), prepared: int = Query(1)):
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached:
        if race_id.startswith("nar-") and str(cached.get("date") or "")==_today_iso():
            hs=[h for h in cached.get("horses",[]) or [] if not h.get("scratched")]
            weights=sum(1 for h in hs if int(h.get("bodyWeight") or 0)>250)
            weight_missing=bool(hs) and weights<max(1,math.ceil(len(hs)*.80))
            result_missing=_nar_result_should_be_available(cached) and not _snapshot_final(cached)
            if refresh or weight_missing or result_missing:_schedule_fast_card_refresh(race_id,0)
        return _compact_display_snapshot(cached)
    quick=_fast_local_race_detail(race_id)
    if quick:
        _store_fast_snapshot(quick)
        return _compact_display_snapshot(quick)
    _schedule_fast_card_refresh(race_id,0)
    return JSONResponse(status_code=202,content={"status":"preparing","raceId":race_id})


@app.post("/api/v1/race/{race_id}/diagnosis-refresh")
def diagnosis_refresh(race_id: str):
    """Local-only diagnosis refresh. External history is prepared by the queue."""
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached:
        pm=cached.get("preparedMeta") or {}
        if pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady"):
            return {
                "status":"done","raceId":race_id,"engineVersion":PREDICTION_ENGINE_VERSION,
                "race":_compact_display_snapshot(cached),"cached":True,
            }
    snap=_build_fast_diagnosis_snapshot(race_id,allow_network=False)
    if not snap:
        return JSONResponse(status_code=202,content={"status":"preparing","raceId":race_id})
    ready=bool((snap.get("preparedMeta") or {}).get("diagnosisReady"))
    return {
        "status":"done" if ready else "preparing",
        "raceId":race_id,
        "engineVersion":PREDICTION_ENGINE_VERSION,
        "race":_compact_display_snapshot(snap),
        "cached":False,
    }


@app.get("/api/v1/race/{race_id}/version")
def snapshot_version(race_id: str):
    conn=sqlite3.connect(PREPARED_STORE.path,timeout=2)
    try:
        row=conn.execute("SELECT json_extract(payload,'$.preparedMeta.revision'),updated_at FROM prepared_races WHERE race_id=?",(race_id,)).fetchone()
        if not row:raise HTTPException(status_code=404,detail="snapshot not found")
        return {"revision":row[0] or "", "updatedAt":row[1]}
    finally:conn.close()


@app.get("/api/v1/race/{race_id}/horse/{horse_no}")
def horse_snapshot(race_id: str, horse_no: int):
    conn=sqlite3.connect(PREPARED_STORE.path,timeout=2)
    try:
        row=conn.execute("SELECT payload FROM horse_snapshots WHERE race_id=? AND horse_no=?",(race_id,horse_no)).fetchone()
        if not row:raise HTTPException(status_code=404,detail="horse snapshot not found")
        return json.loads(row[0])
    finally:conn.close()


@app.get("/api/v1/prewarm-status")
def prewarm_status(date: str = Query(""), circuit: str = Query("")):
    key=f"{date}|{_clean(circuit) or 'all'}" if date else ""
    with _prewarm_lock:
        state=dict(_prewarm_state.get(key) or {}) if key else {k:dict(v) for k,v in _prewarm_state.items()}
    db=PREPARED_STORE.status(date,_clean(circuit))
    return {"build": "v107","state":state,"prepared":db}


@app.get("/api/v1/race/{race_id}/collect")
def collect_race_info(
    race_id: str,
    force: int = Query(1),
    horse_no: int | None = Query(None, ge=1, le=99),
):
    """Retry enrichment + prior-race collection for the selected race.

    The previous UI already called this URL, but the server route was missing, so the
    request always returned 404 and the app showed the history-fetch failure.
    Keep the work asynchronous so the button returns immediately and the
    existing polling UI can refresh the completed data.
    """
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached and (cached.get("date","")!=_today_iso() or _snapshot_final(cached)):
        return {"status":"saved","raceId":race_id,"historySearch":cached.get("historySearch",{}),"enrichmentSearch":cached.get("enrichmentSearch",{})}
    detail = nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:
        raise HTTPException(status_code=404, detail="race not found")

    force_flag = bool(force)

    # Re-run supplemental sources (netkeiba / configured extras) without blocking.
    try:
        enrich = _start_enrichment(race_id, detail, force=force_flag, horse_no=horse_no)
    except Exception as exc:
        print("collect enrichment start failed", race_id, exc)
        enrich = {"status":"unavailable","sources":[],"error":str(exc)}

    # Re-run official history only when it is actually incomplete. Avoid launching
    # a duplicate worker while the same race is already running.
    history = _race_history_status(race_id)
    try:
        if race_id.startswith("nar-"):
            names = [str(h.get("name") or "") for h in detail.get("horses", []) if h.get("name")]
            cov = _history_counts(names, detail.get("date") or "9999-12-31")
            if _history_is_enough(cov, int((history or {}).get("monthsDone") or 0)):
                history = {"status":"done","monthsDone":int((history or {}).get("monthsDone") or 0),
                           "maxMonths":int((history or {}).get("maxMonths") or 0),"coverage":cov,"error":"",
                           "source":(history or {}).get("source") or "NAR公式ローカル履歴"}
            elif not history or history.get("status") != "running":
                history = _start_race_history_search(
                    race_id, detail.get("date") or _today_iso(), names,
                    force=force_flag or bool(history and history.get("status") == "error")
                )
        else:
            cov = _central_detail_coverage(detail)
            total = int(cov.get("totalHorses") or 0)
            resolved = int(cov.get("horsesResolved") or cov.get("horsesWith5Plus") or 0)
            if total == 0 or assess_career_readiness(detail).get("ready"):
                history = {"status":"done","monthsDone":int((history or {}).get("monthsDone") or 0),
                           "maxMonths":int((history or {}).get("maxMonths") or 0),"coverage":cov,"error":"",
                           "source":(history or {}).get("source") or "JRA公式 競走馬情報5走補完"}
            elif not history or history.get("status") != "running":
                history = _start_central_history_search(
                    race_id, detail.get("date") or _today_iso(),
                    force=force_flag or bool(history and history.get("status") == "error")
                )
    except Exception as exc:
        print("collect history start failed", race_id, exc)
        history = history or {"status":"error","monthsDone":0,"maxMonths":0,"coverage":{},"error":str(exc),"source":""}

    # Drop stale display snapshots so the next poll can see newly collected runs.
    try:
        PREPARED_STORE.delete(race_id)
    except Exception:
        pass
    with _detail_cache_lock:
        _detail_cache.pop(race_id, None)

    return {
        "status":"started",
        "raceId":race_id,
        "horseNumber":horse_no,
        "historySearch":history or {"status":"done","coverage":{}},
        "enrichmentSearch":enrich,
    }


@app.get("/api/v1/payouts/{race_id}")
def payout_refresh(race_id:str):
    """Fetch only payouts; do not rebuild history/AI."""
    saved=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not saved:raise HTTPException(status_code=404,detail="race not found")
    existing=((saved.get("result") or {}).get("payouts") or [])
    if existing:
        return {"raceId":race_id,"payouts":existing,"source":(saved.get("result") or {}).get("payoutSource") or "保存済み","cached":True}

    payouts=[];source="";error=""
    if race_id.startswith("nar-"):
        payouts,src=_fetch_nar_payouts_only(saved)
        source="NAR公式" if payouts else ""
        error="" if payouts else src
        if not payouts:
            try:
                nk=_netkeiba_current_result(saved) or {}
                payouts=nk.get("payouts") or []
                if payouts:source="netkeiba結果"
            except Exception as exc:
                error=(error+" | "+str(exc)).strip(" |")
    else:
        try:
            result_cname=str(saved.get("resultCname") or "")
            if not result_cname:
                cname=_jra_find_cname(str(saved.get("date") or ""),str(saved.get("track") or ""),int(saved.get("raceNumber") or 0))
                if cname:result_cname=_jra_result_cname_from_card(cname)
            official=_jra_parse_result(result_cname,saved) if result_cname else None
            payouts=((official or {}).get("result") or {}).get("payouts") or []
            if payouts:source="JRA公式"
        except Exception as exc:
            error=str(exc)
        if not payouts:
            try:
                nk=_netkeiba_current_result(saved) or {}
                payouts=nk.get("payouts") or []
                if payouts:source="netkeiba結果"
            except Exception as exc:
                error=(error+" | "+str(exc)).strip(" |")

    if payouts:
        for store_get,store_put in (
            (lambda:PREPARED_STORE.get(race_id)[0],lambda d:PREPARED_STORE.put(d,force=True)),
            (lambda:RACEDB.get_race(race_id)[0],lambda d:RACEDB.upsert_race(d)),
        ):
            try:
                d=store_get()
                if not d:continue
                res=d.get("result")
                if not isinstance(res,dict):res={};d["result"]=res
                res["payouts"]=payouts;res["payoutSource"]=source;res.pop("payoutError",None)
                store_put(d)
            except Exception as exc:
                print("payout snapshot patch failed",race_id,exc)
    return {"raceId":race_id,"payouts":payouts,"source":source,"cached":False,"error":error[:240]}

def _merge_live_market_rows(race_id:str, fresh_rows:list[dict], saved:dict|None=None)->list[dict]:
    """Preserve the best known live fields per horse when a source returns a partial table.

    A live odds page can briefly omit one or more runners while updating.  Never let
    that sparse response erase previously captured odds/body weight for other horses.
    Fresh non-empty fields win; the latest RaceDB point and saved race snapshot fill gaps.
    """
    by_no:dict[int,dict]={}
    saved=saved or {}
    for h in (saved.get("horses") or []):
        try:no=int(h.get("horseNumber") or 0)
        except Exception:no=0
        if not no:continue
        z={"horseNumber":no}
        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","oddsForecast",
                  "referenceBodyWeight","referenceBodyWeightDate","status","scratched","oddsSource"):
            if h.get(k) not in (None,""):z[k]=h.get(k)
        by_no[no]=z
    try:
        for h in RACEDB.odds_latest(race_id) or []:
            no=int(h.get("horseNumber") or 0)
            if not no:continue
            z=by_no.setdefault(no,{"horseNumber":no})
            for k in ("winOdds","popularity","oddsSource"):
                if z.get(k) in (None,"") and h.get(k) not in (None,""):z[k]=h.get(k)
    except Exception as exc:
        print("odds preserve read failed",race_id,exc)
    for h in fresh_rows or []:
        try:no=int(h.get("horseNumber") or 0)
        except Exception:no=0
        if not no:continue
        z=by_no.setdefault(no,{"horseNumber":no})
        for k,v in h.items():
            if k=="horseNumber":continue
            if v not in (None,""):z[k]=v
    return [by_no[k] for k in sorted(by_no)]

@app.get("/api/v1/odds-refresh/{race_id}")
def odds_refresh(race_id:str, force: int = Query(0)):
    saved=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    saved_has_odds=bool(saved and any((h.get("winOdds") not in (None,"") and float(h.get("winOdds") or 0)>0) for h in (saved.get("horses") or [])))
    saved_horses=(saved.get("horses") or []) if saved else []
    saved_has_weights=bool(saved_horses and all(h.get("bodyWeight") not in (None,"") for h in saved_horses if not h.get("scratched")))
    if saved and saved.get("date")!=_today_iso() and saved_has_odds:
        return {"raceId":race_id,"horses":saved_horses,"oddsSource":saved.get("oddsSource") or "保存済み","storedInRaceDB":True,"oddsUpdatedAt":saved.get("oddsUpdatedAt") or ""}
    if saved and _snapshot_final(saved) and saved_has_odds and saved_has_weights:
        return {"raceId":race_id,"horses":saved_horses,"oddsSource":saved.get("oddsSource") or "保存済み","storedInRaceDB":True,"oddsUpdatedAt":saved.get("oddsUpdatedAt") or ""}
    horses=[]; source=""
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if m:
            odds=_nar_live_odds(m.group(2),m.group(1),int(m.group(3)),bool(force))
            merged={int(no):dict(z or {}) for no,z in odds.items()}
            # NAR current body weight is published on the official DebaTable.
            # Pull it directly instead of trying to resolve a JRA-style netkeiba race id.
            if not merged or any(not (z or {}).get("bodyWeight") for z in merged.values()):
                try:
                    detail=dict(saved or {})
                    detail.update({"id":race_id,"date":m.group(1),"track":m.group(2),"raceNumber":int(m.group(3))})
                    if not detail.get("horses"):
                        try:
                            qd=_fast_local_race_detail(race_id)
                            if qd:detail=qd
                        except Exception:pass
                    for h in _nar_official_card_rows_fast(detail):
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("bodyWeight","bodyWeightChange","status","scratched"):
                            if z.get(k) in (None,"") and h.get(k) not in (None,""):z[k]=h.get(k)
                    if merged and not odds:source="NAR公式出馬表"
                except Exception as exc:print("NAR official body weight fallback failed",race_id,exc)
            # v232: before official live odds/weights are posted, fill the screen with
            # netkeiba NAR predicted odds and any current weight already exposed there.
            try:
                detail=dict(saved or {})
                detail.update({"id":race_id,"date":m.group(1),"track":m.group(2),"raceNumber":int(m.group(3))})
                nk=_nar_netkeiba_preview_rows(detail,bool(force)) or {}
                for no,z0 in nk.items():
                    z=merged.setdefault(int(no),{})
                    official_live=bool(z.get("winOdds") and not z.get("oddsForecast"))
                    if not official_live and z0.get("winOdds"):
                        z["winOdds"]=z0.get("winOdds");z["popularity"]=z0.get("popularity");z["oddsSource"]=z0.get("oddsSource");z["oddsForecast"]=bool(z0.get("oddsForecast"))
                    for k in ("bodyWeight","bodyWeightChange"):
                        if z.get(k) in (None,"") and z0.get(k) not in (None,""):z[k]=z0.get(k)
                if nk and not odds:source="netkeiba予想オッズ"
            except Exception as exc:print("NAR netkeiba preview fallback failed",race_id,exc)
            # Always attach a truthful previous-race weight reference while current weigh-in is pending.
            if saved:
                saved_by={int(h.get("horseNumber") or 0):h for h in (saved.get("horses") or [])}
                for no,h0 in saved_by.items():
                    z=merged.setdefault(no,{})
                    if not z.get("bodyWeight"):
                        rw,rd=_reference_weight_from_horse(h0)
                        if rw:z["referenceBodyWeight"]=rw;z["referenceBodyWeightDate"]=rd
            if saved and _snapshot_final(saved):
                for f in ((saved.get("result") or {}).get("finishers") or []):
                    no=int(f.get("horseNumber") or 0)
                    if not no:continue
                    z=merged.setdefault(no,{})
                    for k in ("bodyWeight","bodyWeightChange","popularity","winOdds"):
                        if z.get(k) in (None,"") and f.get(k) not in (None,""):z[k]=f.get(k)
            for no,z in sorted(merged.items()):
                horses.append({"horseNumber":int(no),**{k:v for k,v in z.items() if v is not None}})
            if not source:source="NAR公式" if odds else (next((str(z.get("oddsSource") or "") for z in merged.values() if z.get("oddsSource")),"") or ("NAR公式出馬表" if horses else ""))
    else:
        mm=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",race_id)
        detail={}
        if mm:
            detail=_jra_program_lookup(mm.group(1),mm.group(2),int(mm.group(3))) or {"date":mm.group(1),"track":mm.group(2),"raceNumber":int(mm.group(3))}
            detail["netkeibaRaceId"]=detail.get("netkeibaRaceId") or _netkeiba_program_race_id(mm.group(1),mm.group(2),int(mm.group(3)))
            merged={}
            # v228: official JRA first. The live/full dde10 card carries odds and body weight.
            try:
                cname=_jra_find_cname(mm.group(1),mm.group(2),int(mm.group(3)))
                if cname:
                    jr=_jra_parse_race(cname,supplement_profiles=False) or {}
                    for h in jr.get("horses",[]) or []:
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                            if h.get(k) not in (None,""):z[k]=h.get(k)
                    if any(float((h.get("winOdds") or 0))>0 or h.get("bodyWeight") for h in (jr.get("horses") or [])):
                        source="JRA公式"
            except Exception as exc: print("fast odds JRA failed",race_id,exc)

            # Secondary public-page fallback only fills fields still missing after JRA official.
            try:
                nk=_netkeiba_live_win_odds(detail,bool(force)) or {}
                for no,z0 in nk.items():
                    z=merged.setdefault(int(no),{})
                    for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                        if z.get(k) in (None,"") and (z0 or {}).get(k) not in (None,""):
                            z[k]=(z0 or {}).get(k)
            except Exception as exc: print("fast odds secondary fallback failed",race_id,exc)

            # Fast shutuba scrape fallback (same page used for the card).
            if not any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):
                try:
                    card_detail=dict(detail);card_detail["id"]=race_id
                    for h in _netkeiba_card_rows_fast(card_detail):
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                            if h.get(k) not in (None,""):z[k]=h.get(k)
                    if any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):source="netkeiba出馬表"
                except Exception as exc:print("fast odds card scrape failed",race_id,exc)

            # Yesterday/final races: result page carries final odds.
            if not any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):
                try:
                    result_detail=(saved or detail or {})
                    nkres=_netkeiba_current_result(result_detail) or {}
                    for f in nkres.get("finishers",[]) or []:
                        no=int(f.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange"):
                            if f.get(k) not in (None,""):z[k]=f.get(k)
                    if any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):source="netkeiba最終"
                except Exception as exc:print("final odds result fallback failed",race_id,exc)

            for no,z in sorted(merged.items()):horses.append({"horseNumber":no,**z})
            if not source and horses:source="netkeiba"
    # v305: a source can momentarily return a sparse odds table. Merge it with the
    # best already-saved per-horse live fields so one missing row never falls back
    # to the endless "取得中" state after another horse was successfully refreshed.
    horses=_merge_live_market_rows(race_id,horses,saved)
    if not source:
        source=next((str(h.get("oddsSource") or "") for h in horses if h.get("oddsSource")),"")
    if horses:
        try:RACEDB.save_odds(race_id,horses,source)
        except Exception as exc:print("RaceDB odds save failed",race_id,exc)
        try:
            snapshot,_=PREPARED_STORE.get(race_id)
            if snapshot:
                by_no={int(h.get("horseNumber") or 0):h for h in horses}
                for h in snapshot.get("horses",[]):
                    update=by_no.get(int(h.get("horseNumber") or 0),{})
                    for key in ("winOdds","popularity","bodyWeight","bodyWeightChange","oddsForecast","referenceBodyWeight","referenceBodyWeightDate","status","scratched"):
                        if update.get(key) is not None:h[key]=update[key]
                    if update.get("oddsSource"):h["oddsSource"]=update.get("oddsSource")
                snapshot["oddsSource"]=source
                snapshot["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
                PREPARED_STORE.put(snapshot,force=True)
                try:RACEDB.upsert_race(snapshot)
                except Exception:pass
        except Exception as exc:print("odds snapshot update failed",exc)
        try:
            with _site_bootstrap_lock:_site_bootstrap_cache.pop(_today_iso(),None)
        except Exception:pass
    if not horses:
        try:
            stored=RACEDB.odds_latest(race_id) or []
            if stored:
                horses=stored
                source=next((str(x.get("oddsSource") or "") for x in stored if x.get("oddsSource")),"保存済み")
        except Exception:pass
    live=[h for h in horses if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
    odds_count=sum(1 for h in live if float(h.get("winOdds") or 0)>0)
    return {"raceId":race_id,"horses":horses,"oddsSource":source,
            "oddsUpdatedAt":_now_jst().strftime("%H:%M:%S"),"storedInRaceDB":bool(horses),
            "fieldCount":len(live),"oddsCount":odds_count,
            "oddsComplete":bool(live) and odds_count==len(live)}


_auto_odds_lock=threading.Lock()
_auto_odds_last:dict[str,float]={}
_auto_odds_state={"running":False,"lastStart":0,"lastFinish":0,"checked":0,"updated":0,"error":""}

def _auto_odds_targets()->list[dict]:
    date=_today_iso();rows=[]
    try:rows.extend(nar_race_summaries(date))
    except Exception:pass
    try:rows.extend(central_race_summaries(date,allow_network=False))
    except Exception:pass
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    out=[]
    for r in rows:
        if not r.get("id") or _snapshot_final(r):continue
        start=_race_minutes_server(r)
        if start>=9999:
            out.append(r);continue
        remain=start-nowm
        if remain < -8:continue
        out.append(r)
    out.sort(key=lambda r:_race_minutes_server(r))
    return out

def _auto_odds_cycle():
    global _auto_odds_state
    with _auto_odds_lock:
        if _auto_odds_state.get("running"):return
        _auto_odds_state.update({"running":True,"lastStart":int(time.time()),"checked":0,"updated":0,"error":""})
    checked=updated=0;errors=[]
    try:
        now=time.time();targets=[]
        nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
        for r in _auto_odds_targets():
            rid=str(r.get("id") or "");start=_race_minutes_server(r)
            remain=(start-nowm) if start<9999 else 9999
            cadence=30 if remain<=30 else 60 if remain<=180 else 180
            last=float(_auto_odds_last.get(rid,0))
            if now-last<cadence:continue
            _auto_odds_last[rid]=now;targets.append(r)
        def one(r):
            rid=str(r.get("id") or "")
            try:
                last_body=None
                for attempt in range(2):
                    last_body=odds_refresh(rid,1)
                    hs=(last_body or {}).get("horses") or []
                    live=[h for h in hs if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
                    got=sum(1 for h in live if float(h.get("winOdds") or 0)>0)
                    weights=sum(1 for h in live if int(h.get("bodyWeight") or 0)>250)
                    if live and got==len(live):
                        return rid,{"complete":True,"odds":got,"field":len(live),"weights":weights}
                    if attempt==0:time.sleep(.15)
                return rid,{"complete":False,"odds":got if 'got' in locals() else 0,
                            "field":len(live) if 'live' in locals() else 0,
                            "weights":weights if 'weights' in locals() else 0}
            except Exception as exc:
                return rid,exc
        workers=max(1,min(20,int(os.getenv("AUTO_ODDS_WORKERS","18")),len(targets))) if targets else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for rid,res in pool.map(one,targets):
                    checked+=1
                    if isinstance(res,dict) and res.get("complete"):
                        updated+=1
                    elif isinstance(res,dict):
                        # Partial tables are not success. Retry on the next short cycle instead
                        # of waiting the normal far-race cadence for a missing runner.
                        _auto_odds_last[rid]=min(float(_auto_odds_last.get(rid,0)),time.time()-20)
                    elif isinstance(res,Exception):errors.append(rid+": "+str(res))
    finally:
        with _auto_odds_lock:
            _auto_odds_state.update({
                "running":False,"lastFinish":int(time.time()),"checked":checked,
                "updated":updated,"error":" | ".join(errors[-5:])
            })

def _auto_odds_loop():
    time.sleep(float(os.getenv("AUTO_ODDS_START_DELAY_SEC","0.7")))
    while True:
        try:_auto_odds_cycle()
        except Exception as exc:print("auto odds cycle failed",exc)
        time.sleep(max(8,int(os.getenv("AUTO_ODDS_LOOP_SEC","10"))))

@app.on_event("startup")
def _start_auto_odds_collector():
    enabled=str(os.getenv("ARVEXQ_AUTO_ODDS","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_auto_odds_loop,daemon=True,name="arvexq-auto-odds").start()

@app.get("/api/v1/odds-auto-status")
def odds_auto_status():
    with _auto_odds_lock:return dict(_auto_odds_state)


@app.post("/api/v1/racedb/analysis/{race_id}")
async def racedb_save_analysis(race_id: str, request: Request):
    try:
        payload=await request.json()
        if not isinstance(payload,dict):raise ValueError("invalid analysis payload")
        payload["raceId"]=race_id
        cached=_prepared_get_fresh(race_id)
        if cached and (cached.get("date")!=_today_iso() or _snapshot_final(cached)):
            return {"ok":True,"raceId":race_id,"stored":False,"frozen":True}
        RACEDB.save_analysis(race_id,payload)
        if cached:
            cached["analysis"]=payload
            PREPARED_STORE.put(cached)
        return {"ok":True,"raceId":race_id,"stored":True}
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc))

@app.get("/api/v1/racedb/analysis/{race_id}")
def racedb_get_analysis(race_id: str):
    return {"raceId":race_id,"analysis":RACEDB.get_analysis(race_id)}

@app.get("/api/v1/model-audit")
def model_audit(date: str = Query(""), days: int = Query(30, ge=1, le=180)):
    end=date or _today_iso()
    try:end_dt=datetime.strptime(end,"%Y-%m-%d").date()
    except Exception:raise HTTPException(status_code=400,detail="date must be YYYY-MM-DD")
    start_dt=end_dt-timedelta(days=max(0,int(days)-1));start=start_dt.isoformat()
    rows=[];cal=[];segments={}
    if not RACEDB.path.exists():return {"version":PRERACE_AUDIT_VERSION,"races":0,"audited":0,"start":start,"end":end}
    conn=sqlite3.connect(RACEDB.path,timeout=3);conn.row_factory=sqlite3.Row
    try:dbrows=conn.execute("SELECT payload FROM race_snapshots WHERE race_date BETWEEN ? AND ? ORDER BY race_date,track,race_no",(start,end)).fetchall()
    finally:conn.close()
    for row in dbrows:
        try:d=json.loads(row["payload"])
        except Exception:continue
        a=d.get("predictionAudit") if isinstance(d.get("predictionAudit"),dict) else _prediction_audit_from_lock(d)
        if not a:continue
        rows.append(a)
        seg=str(a.get("circuit") or "不明");z=segments.setdefault(seg,{"races":0,"hits":0,"marked":0});z["races"]+=1;z["hits"]+=1 if a.get("honHit") else 0;z["marked"]+=1 if a.get("winnerMarked") else 0
        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else {};winner=int(a.get("winnerNo") or 0)
        for h in lock.get("horses") or []:
            try:p=max(0.0,min(1.0,float(h.get("decisionProbability") or 0)))
            except Exception:continue
            cal.append((p,1 if int(h.get("horseNumber") or 0)==winner else 0))
    n=len(rows);hits=sum(1 for a in rows if a.get("honHit"));marked=sum(1 for a in rows if a.get("winnerMarked"));top2=sum(1 for a in rows if a.get("top2Hit"));top3=sum(1 for a in rows if a.get("top3Hit"));hc=[a for a in rows if a.get("highConfidence")]
    reasons={}
    for a in rows:
        if a.get("honHit"):continue
        k=str(a.get("reason") or "その他");reasons[k]=reasons.get(k,0)+1
    bins=[];ece=0.0
    for bi in range(10):
        lo=bi/10;hi=(bi+1)/10;vals=[x for x in cal if (x[0]>=lo and (x[0]<hi or (bi==9 and x[0]<=hi)))]
        if not vals:continue
        pm=sum(x[0] for x in vals)/len(vals);ar=sum(x[1] for x in vals)/len(vals);ece+=abs(pm-ar)*len(vals)/max(1,len(cal));bins.append({"lo":lo,"hi":hi,"count":len(vals),"predicted":round(pm,4),"actual":round(ar,4),"gap":round(ar-pm,4)})
    segout={k:{"races":v["races"],"top1":round(v["hits"]/v["races"],4) if v["races"] else 0,"winnerMarked":round(v["marked"]/v["races"],4) if v["races"] else 0} for k,v in segments.items()}
    learning={}
    for c in ("地方","中央"):
        try:learning[c]=_winner_learning_profile({"date":end,"circuit":c})
        except Exception as exc:learning[c]={"version":WINNER_LEARNING_VERSION,"active":False,"reason":"profile-error","error":str(exc)[:120]}
    return {"version":PRERACE_AUDIT_VERSION,"start":start,"end":end,"races":len(dbrows),"audited":n,"learningReady":n>=WINNER_LEARNING_MIN_RACES,"learning":learning,
            "honTop1":round(hits/n,4) if n else 0,"winnerMarked":round(marked/n,4) if n else 0,"winnerTop2":round(top2/n,4) if n else 0,"winnerTop3":round(top3/n,4) if n else 0,
            "highConfidence":{"races":len(hc),"hits":sum(1 for a in hc if a.get("honHit")),"rate":round(sum(1 for a in hc if a.get("honHit"))/len(hc),4) if hc else 0},
            "brier":round(sum(float(a.get("brier") or 0) for a in rows)/n,6) if n else None,"logLoss":round(sum(float(a.get("logLoss") or 0) for a in rows)/n,6) if n else None,
            "calibration":{"horseSamples":len(cal),"ece":round(ece,6) if cal else None,"bins":bins},"segments":segout,
            "missReasons":dict(sorted(reasons.items(),key=lambda kv:(-kv[1],kv[0]))),"audits":rows[-100:]}


@app.get("/api/v1/model-learning")
def model_learning(date: str = Query(""), circuit: str = Query("地方")):
    target=date or _today_iso();c=_clean(circuit) or "地方"
    if c not in {"中央","地方"}:raise HTTPException(status_code=400,detail="circuit must be 中央 or 地方")
    try:datetime.strptime(target,"%Y-%m-%d")
    except Exception:raise HTTPException(status_code=400,detail="date must be YYYY-MM-DD")
    return _winner_learning_profile({"date":target,"circuit":c})


@app.get("/api/v1/racedb-status")
def racedb_status(date: str = "", circuit: str = ""):
    return {"build":"v302-fullcard-livefix","status":RACEDB.status(date,_clean(circuit)),"dataCoreVersion":ARVEXQ_DATA_CORE_VERSION,"continuousUpdater":True,"trackSpeed":True,"preRaceAudit":True,"safeWinnerLearning":True,"note":"Data Core + T-5分最終固定 + 日付ブロックTRAIN/TUNE/PROMOTION。SHADOWは選定・昇格に使わず監査専用。市場情報はwinner学習に不使用。"}

@app.get("/api/v1/racedb-race/{race_id}")
def racedb_race(race_id:str):
    detail,updated=RACEDB.get_race(race_id)
    if not detail:raise HTTPException(status_code=404,detail="RaceDB snapshot not found")
    return {"updatedAt":updated,"detail":detail,"oddsLatest":RACEDB.odds_latest(race_id)}

_racedb_daemon_started=False
_racedb_daemon_lock=threading.Lock()

def _racedb_live_cycle()->None:
    today=_today_iso();rows=[]
    _schedule_live_refresh(today,False)
    _schedule_central_refresh(today,False)
    try:rows.extend(nar_race_summaries(today))
    except Exception as exc:print("RaceDB NAR list failed",exc)
    try:rows.extend(central_race_summaries(today,allow_network=True,force=False))
    except Exception as exc:print("RaceDB JRA list failed",exc)
    if rows:_schedule_prewarm(rows,today,"")
    # Odds are much more volatile than past runs.  Only poll a few upcoming races.
    if not bool(int(os.getenv("RACEDB_AUTO_ODDS","1"))):return
    nowm=_now_jst().hour*60+_now_jst().minute;window=int(os.getenv("RACEDB_ODDS_WINDOW_MIN","90"));limit=max(1,int(os.getenv("RACEDB_ODDS_MAX_RACES","4")))
    upcoming=[]
    for r in rows:
        if r.get("result"):continue
        t=str(r.get("startTime") or "")
        m=re.match(r"^(\d{1,2}):(\d{2})",t)
        if not m:continue
        rm=int(m.group(1))*60+int(m.group(2));delta=rm-nowm
        if -5<=delta<=window:upcoming.append((delta,r))
    upcoming.sort(key=lambda x:x[0])
    for _,r in upcoming[:limit]:
        try:odds_refresh(str(r.get("id") or ""))
        except Exception as exc:print("RaceDB automatic odds failed",r.get("id"),exc)

def _start_racedb_daemon()->None:
    global _racedb_daemon_started
    if str(os.getenv("ARVEXQ_COMMERCIAL_COLLECTOR","1")).lower() in {"1","true","yes","on"}:return
    if not bool(int(os.getenv("RACEDB_AUTO_UPDATE","1"))):return
    with _racedb_daemon_lock:
        if _racedb_daemon_started:return
        _racedb_daemon_started=True
    def worker():
        # Short initial delay lets app import/route registration finish.
        time.sleep(float(os.getenv("RACEDB_START_DELAY_SEC","2")))
        while True:
            try:_racedb_live_cycle()
            except Exception as exc:print("RaceDB live cycle failed",exc)
            time.sleep(max(30,int(os.getenv("RACEDB_UPDATE_SEC","120"))))
    threading.Thread(target=worker,daemon=True,name="RaceDB-live-updater").start()

@app.get("/api/v1/enrichment-status/{race_id}")
def enrichment_status(race_id:str):
    return _enrichment_status(race_id)

@app.get("/api/v1/enrichment-schema")
def enrichment_schema():
    return {"priority":"official-first","builtIn":["JRA公式","NAR公式","netkeiba"],"extraFeeds":{"env":"EXTRA_RACE_FEEDS","format":"NAME=url;NAME2=url2"},"note":"公開ページ/APIのみ。ログイン・CAPTCHA・規約で自動取得不可のサイトは対象外"}

@app.get("/build")
def build_info():
    return {
        "build":"v324","appVersion":"14.24-v325-home-race-boxes",
        "predictionEngine":PREDICTION_ENGINE_VERSION,
        "navigation":"top-venue-race","recentRuns":5,
        "localFirst":True,"selectedRacePriority":0,"trackPrewarm":3,
        "commercialCollector":True,"duplicateUpdaterDisabled":True,
        "autoDiagnosis":True,"autoOdds":True,"oddsUsedInPrediction":False,"raceVolatility":"硬/標/荒/大荒・pre-race no-odds",
        "narHydration":"sync_daily/sync_month","history":"JRA one-page / NAR month cache",
        "raceDataBank":True,"browserDetailCache":True,"gzip":True,"liveEnvironment":True,"environmentRefreshSec":45,
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/venue", response_class=HTMLResponse)
@app.get("/race", response_class=HTMLResponse)
def home():
    # Keep first paint light. Race list/detail data is loaded from Cloudflare/D1
    # by the browser; Render remains the fallback for live/manual refreshes.
    boot='<script>window.__ARVEXQ_BOOTSTRAP__=null;</script>'
    html=INDEX.replace(
        '<script src="/app-v324.js"></script>',
        boot+'\n<script src="/app-v324.js"></script>'
    )
    return HTMLResponse(html, headers={
        "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
        "Pragma":"no-cache","Expires":"0"
    })


from arvexq.ui.icon_assets import load_icons as _load_arvexq_icons
ARVEXQ_ICONS = _load_arvexq_icons()


@app.get("/arvexq-icon-v175-{size}.png")
def arvexq_icon(size: int):
    if str(size) not in ARVEXQ_ICONS:raise HTTPException(status_code=404,detail="icon not found")
    return Response(base64.b64decode(ARVEXQ_ICONS[str(size)]),media_type="image/png",headers={"Cache-Control":"public,max-age=86400"})


ARVEXQ_TOUCH_ICON_180 = read_binary_asset("arvexq-touch-icon-180.bin")

CINEMATIC_HERO_WEBP = read_binary_asset("cinematic-hero-webp.webp")
CINEMATIC_DETAIL_WEBP = read_binary_asset("cinematic-detail-webp.webp")
@app.get("/arvexq-touch-v175.png")
def arvexq_touch_icon():
    return Response(ARVEXQ_TOUCH_ICON_180,media_type="image/png",headers={"Cache-Control":"no-store,max-age=0"})


@app.get("/arvexq-racing-detail.webp")
def cinematic_detail_photo():
    return Response(CINEMATIC_DETAIL_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=86400"})

@app.get("/arvexq-racing-hero.webp")
def cinematic_hero():
    return Response(CINEMATIC_HERO_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=86400"})


@app.get("/arvexq-logo.webp")
def arvexq_logo():
    return Response(ARVEXQ_LOGO_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=31536000,immutable"})

@app.get("/hero-horse.webp")
def hero_horse():
    return Response(HERO_HORSE_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/pace-preview.webp")
def pace_preview():
    return Response(PACE_PREVIEW_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/version.json")
def version_json():
    return Response('{"build":"v324","shell":"core-data-guard","model":"v317-consensus-rebuild"}', media_type="application/json", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/styles-arvexq-v324.css")
@app.get("/styles-arvexq-v321.css")
@app.get("/styles-arvexq-v320.css")
@app.get("/styles-arvexq-v319.css")
@app.get("/styles-arvexq-v318.css")
@app.get("/styles-arvexq-v317.css")
@app.get("/styles-arvexq-v316.css")
@app.get("/styles-arvexq-v315.css")
@app.get("/styles-arvexq-v314.css")
@app.get("/styles-arvexq-v313.css")
@app.get("/styles-arvexq-v312.css")
@app.get("/styles-arvexq-v308.css")
@app.get("/styles-arvexq-v307.css")
@app.get("/styles-arvexq-v306.css")
@app.get("/styles-arvexq-v305.css")
@app.get("/styles-arvexq-v303.css")
@app.get("/styles-arvexq-v130.css")
@app.get("/styles-arvexq-v91.css")
@app.get("/styles-arvexq-v88.css")
@app.get("/styles-v86.css")
def styles(request: Request):
    current=request.url.path=="/styles-arvexq-v324.css"
    cache="public, max-age=31536000, immutable" if current else "no-cache, must-revalidate"
    return Response(CSS, media_type="text/css", headers={"Cache-Control":cache})

@app.get("/app-v324.js")
@app.get("/arvexq-app-v324.js")
@app.get("/app-v321.js")
@app.get("/arvexq-app-v321.js")
@app.get("/app-v320.js")
@app.get("/arvexq-app-v320.js")
@app.get("/app-v319.js")
@app.get("/arvexq-app-v319.js")
@app.get("/app-v318.js")
@app.get("/arvexq-app-v318.js")
@app.get("/app-v317.js")
@app.get("/arvexq-app-v317.js")
@app.get("/app-v316.js")
@app.get("/arvexq-app-v316.js")
@app.get("/app-v315.js")
@app.get("/arvexq-app-v315.js")
@app.get("/app-v314.js")
@app.get("/arvexq-app-v314.js")
@app.get("/app-v313.js")
@app.get("/arvexq-app-v313.js")
@app.get("/app-v312.js")
@app.get("/arvexq-app-v312.js")
@app.get("/app-v308.js")
@app.get("/arvexq-app-v308.js")
@app.get("/app-v307.js")
@app.get("/arvexq-app-v307.js")
@app.get("/app-v306.js")
@app.get("/arvexq-app-v306.js")
@app.get("/app-v305.js")
@app.get("/arvexq-app-v305.js")
@app.get("/app-v303.js")
@app.get("/arvexq-app-v303.js")
@app.get("/app-v133.js")
@app.get("/app-v132.js")
@app.get("/app-v131.js")
@app.get("/app-v130.js")
@app.get("/app-v91.js")
@app.get("/app-v88.js")
@app.get("/app-v87.js")
@app.get("/app-v86-fix1.js")
def appjs(request: Request):
    current=request.url.path in {"/app-v324.js","/arvexq-app-v324.js"}
    cache="public, max-age=31536000, immutable" if current else "no-cache, must-revalidate"
    return Response(JS, media_type="application/javascript", headers={"Cache-Control":cache})

@app.get("/manifest-v86.webmanifest")
@app.get("/manifest-arvexq-v175.webmanifest")
@app.get("/manifest-arvexq-v173.webmanifest")
@app.get("/manifest-arvexq-v130.webmanifest")
@app.get("/manifest-arvexq-v88.webmanifest")
def manifest():
    return Response(MANIFEST, media_type="application/manifest+json", headers={"Cache-Control":"public, max-age=3600"})

@app.get("/sw-v324-reset.js")
@app.get("/sw-v321-reset.js")
@app.get("/sw-v320-reset.js")
@app.get("/sw-v319-reset.js")
@app.get("/sw-v318-reset.js")
@app.get("/sw.js")
def service_worker():
    return Response(SW, media_type="application/javascript", headers={"Service-Worker-Allowed":"/", "Cache-Control":"no-store, max-age=0"})


# Start the v86 RaceDB updater after module initialization.
# ARVEXQ_DATABANK_REGISTRY
register_legacy_sources(globals())

_start_racedb_daemon()


# v158 upset targeting / race selection


# v239: simplified horse detail and persistent live iframe


