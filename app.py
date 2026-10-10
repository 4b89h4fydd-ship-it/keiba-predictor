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


def _clean(value: str | None) -> str:
    return (value or "").strip().replace("\u3000", " ")


def _int(value: str | None, default: int = 0) -> int:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def _float(value: str | None, default: float = 0.0) -> float:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _carried_weight(value: str | None, default: float = 0.0) -> float:
    """斤量セルを数値にする。NAR公式は減量騎手を「▲ 51.0」「☆55.0」のように
    印つきで出すため、float() に直接渡すと失敗して 0kg 扱いになっていた。"""
    s = _clean(value).replace(",", "")
    if not s:
        return default
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return default
    try:
        return float(m.group(0))
    except ValueError:
        return default


def _iso_date(yyyymmdd: str) -> str:
    s = re.sub(r"\D", "", yyyymmdd)
    if len(s) != 8:
        return yyyymmdd
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def _start_time(hhmm: str) -> str:
    s = re.sub(r"\D", "", hhmm)
    if len(s) == 3:
        s = "0" + s
    if len(s) != 4:
        return _clean(hhmm)
    return f"{s[:2]}:{s[2:]}"


def _time_seconds(raw: str) -> float:
    """NAR result time e.g. '2043' => 2:04.3, '594' => 59.4."""
    s = re.sub(r"[^0-9]", "", _clean(raw))
    if not s:
        return 0.0
    if len(s) <= 3:
        return int(s) / 10.0
    minutes = int(s[:-3])
    sec_tenths = int(s[-3:])
    return minutes * 60 + sec_tenths / 10.0


def _normalize_sex(value: str) -> str:
    s = _clean(value)
    if s in {"セン", "セ", "騸"}:
        return "セ"
    if s.startswith("牝"):
        return "牝"
    return "牡"



def _scratch_status(value: str) -> str:
    s=_clean(value)
    if not s:return ""
    if "競走除外" in s or "除外" in s:return "除外"
    if "出走取消" in s or "取消" in s:return "出走取消"
    if "欠場" in s:return "欠場"
    return ""


def _normalize_weather(value: str) -> str:
    s = _clean(value)
    for v in ("晴", "曇", "小雨", "雨", "小雪", "雪"):
        if v in s:
            return v
    return "不明"


def _normalize_condition(value: str) -> str:
    s = _clean(value)
    # Banei uses a moisture percentage rather than 良/稍重/重/不良.
    for v in ("不良", "稍重", "重", "良"):
        if v in s:
            return v
    return "不明"


def _stable_id(*parts: object) -> int:
    digest = hashlib.blake2s("|".join(map(str, parts)).encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFF


def read_csv_from_zip(zip_bytes: bytes, suffix: str) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        matches = [n for n in zf.namelist() if n.lower().endswith(suffix.lower())]
        if not matches:
            return []
        text = decode_csv_bytes(zf.read(matches[0]))
    return [row for row in csv.reader(io.StringIO(text)) if row]


def strip_header(rows: list[list[str]]) -> list[list[str]]:
    if rows and rows[0] and _clean(rows[0][0]) == "競馬場":
        return rows[1:]
    return rows


def _top_level_tokens(text: str) -> list[str]:
    """Split a NAR corner-order string while keeping '(2,7)' as one group."""
    text = _clean(text)
    if not text:
        return []
    tokens: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            if buf:
                tokens.append("".join(buf).strip())
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf).strip())
    return tokens


def parse_corner_order(text: str) -> dict[int, int]:
    """
    Convert NAR's race-level passage order to {horse_number: position}.
    Parenthesized groups are treated as tied; hyphens are distance separators,
    not missing horses, so numbers remain sequential positions.
    """
    positions: dict[int, int] = {}
    rank = 1
    for token in _top_level_tokens(text):
        tied = token.startswith("(") and token.endswith(")")
        nums = [int(x) for x in re.findall(r"\d+", token)]
        if not nums:
            continue
        if tied and len(nums) > 1:
            for horse_no in nums:
                positions[horse_no] = rank
            rank += len(nums)
        else:
            for horse_no in nums:
                positions[horse_no] = rank
                rank += 1
    return positions


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


def normalize_central_race(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    date = _clean(str(raw.get("date") or ""))
    track = _clean(str(raw.get("track") or ""))
    race_no = _int(str(raw.get("raceNumber") or raw.get("race_no") or "0"))
    if not date or not track or race_no <= 0:
        return None
    horses = raw.get("horses") if isinstance(raw.get("horses"), list) else []
    rid = _clean(str(raw.get("id") or f"jra-{date}-{track}-{race_no:02d}"))
    out = dict(raw)
    out.update({
        "id": rid, "circuit": "中央", "date": date, "track": track, "raceNumber": race_no,
        "title": raw.get("title") or f"{race_no}R", "distance": int(raw.get("distance") or 0),
        "condition": raw.get("condition") or "不明", "weather": raw.get("weather") or "不明",
        "surface": raw.get("surface") or raw.get("trackType") or "",
        "fieldSize": int(raw.get("fieldSize") or len(horses)),
        "racePrize1": int(raw.get("racePrize1") or raw.get("prize1") or 0),
        "startTime": raw.get("startTime") or raw.get("actualStartTime") or "",
        "scheduledStartTime": raw.get("scheduledStartTime") or raw.get("originalStartTime") or raw.get("startTime") or raw.get("actualStartTime") or "",
        "horses": horses, "source": raw.get("source") or "中央本番フィード",
    })
    out["startTimeChanged"] = bool(out.get("scheduledStartTime") and out.get("startTime") and out.get("scheduledStartTime") != out.get("startTime"))
    return out


JRA_TRACK_CODES = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
JRA_TRACK_CODE_BY_NAME = {v:k for k,v in JRA_TRACK_CODES.items()}
JRA_MEETING_DAY_RE = re.compile(r"(\d+)回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)(\d+)日")
JRA_CNAME_RE = re.compile(r"pw01dde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_HORSE_CNAME_RE = re.compile(r"pw01dud\d{12,}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_RESULT_CNAME_RE = re.compile(r"pw01sde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
_jra_cache_lock = threading.Lock()
_jra_text_cache: dict[str, tuple[float,str]] = {}

def _jra_request(url: str, cname: str | None = None, cache_sec: int = 1800) -> str:
    key=url+"|"+(cname or "")
    now=time.time()
    with _jra_cache_lock:
        hit=_jra_text_cache.get(key)
        if hit and now-hit[0] < cache_sec:
            return hit[1]
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/6.2; +https://www.jra.go.jp/)","Accept-Language":"ja,en;q=0.8"}
    data=None
    if cname:
        data=urllib.parse.urlencode({"cname":cname}).encode("ascii")
        headers["Content-Type"]="application/x-www-form-urlencoded"
    req=urllib.request.Request(url,data=data,headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.getenv("JRA_OFFICIAL_TIMEOUT_SEC","4.5"))) as res:
        text=_jra_decode(res.read())
    with _jra_cache_lock:
        _jra_text_cache[key]=(now,text)
    return text

def _jra_norm_cname(value:str)->str:
    return re.sub(r"%2F","/",str(value or ""),flags=re.I)

def _jra_attr_cname(tag, pattern) -> str:
    if not tag: return ""
    blob=" ".join(str(v) for v in tag.attrs.values())+" "+str(tag)
    m=pattern.search(blob)
    return _jra_norm_cname(m.group(0)) if m else ""

JRA_BAD_TITLE_RE = re.compile(r"検索ウィンドウ|緊急情報|重要なお知らせ|お知らせ|関連メニュー|今週の開催|JRAからのお知らせ|インフォメーション|ピックアップ|発売レース|各種サービス|スペシャルコンテンツ|競馬メニュー|開催日程")
JRA_PROGRAM_TRACK_RE = re.compile(r"\d+回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\d+日")
_jra_program_cache_lock=threading.Lock(); _jra_program_cache={}
_jra_cname_lookup_lock=threading.Lock(); _jra_cname_lookup={}

def _jra_program_title(info:str)->str:
    s=re.sub(r"\s+"," ",str(info or "")).strip(); dm=re.search(r"[\d,]{4,5}\s*[（(]",s); prefix=(s[:dm.start()] if dm else s).strip()
    cm=re.search(r"\s+(?:障害)?(?:2歳|3歳|4歳)(?:以上)?",prefix)
    if cm and cm.start()>0:
        named=prefix[:cm.start()].strip()
        if named:return named
    return prefix

def _jra_program_summaries(iso_date:str)->list[dict]:
    now=time.time()
    with _jra_program_cache_lock:
        hit=_jra_program_cache.get(iso_date)
        if hit and now-hit[0]<(60 if iso_date==_today_iso() else 86400):return [dict(x) for x in hit[1]]
    try:d=datetime.strptime(iso_date,"%Y-%m-%d")
    except Exception:return []
    url=f"https://www.jra.go.jp/keiba/calendar{d.year}/{d.year}/{d.month}/{d.strftime('%m%d')}.html"
    try:html=_jra_request(url,None,60 if iso_date==_today_iso() else 86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser"); out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr") or table)
        if "レース番号" not in head or "発走時刻" not in head:continue
        track="";meeting_no=0;day_no=0
        prev=table.find_previous(string=JRA_MEETING_DAY_RE)
        if prev:
            mt=JRA_MEETING_DAY_RE.search(str(prev))
            if mt:meeting_no=int(mt.group(1));track=mt.group(2);day_no=int(mt.group(3))
        if not track:
            node=table.find_previous(["h2","h3","h4","h5","strong","p","div"]);guard=0
            while node is not None and guard<30:
                mt=JRA_MEETING_DAY_RE.search(_jra_text(node))
                if mt:meeting_no=int(mt.group(1));track=mt.group(2);day_no=int(mt.group(3));break
                node=node.find_previous(["h2","h3","h4","h5","strong","p","div"]);guard+=1
        if not track:continue
        track_code=JRA_TRACK_CODE_BY_NAME.get(track,"")
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<3:continue
            c0,c1,c2=(_jra_text(cells[0]),_jra_text(cells[1]),_jra_text(cells[2]))
            rm=re.search(r"(\d{1,2})\s*レース",c0)
            if not rm:continue
            race_no=int(rm.group(1))
            dm=re.search(r"([\d,]{4,5})\s*[（(]([^）)]+)[）)]",c1)
            distance=int(dm.group(1).replace(",","")) if dm else 0;desc=dm.group(2) if dm else ""
            surface="障害" if "障害" in c1 else ("芝" if "芝" in desc else ("ダート" if "ダ" in desc else ""))
            sm=re.search(r"(\d{1,2})時\s*(\d{2})分",c2)
            start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
            title=_jra_program_title(c1) or f"{race_no}R"
            nkid=(f"{d.year:04d}{track_code}{meeting_no:02d}{day_no:02d}{race_no:02d}" if track_code and meeting_no and day_no else "")
            z=normalize_central_race({"id":f"jra-{iso_date}-{track}-{race_no:02d}","date":iso_date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":"不明","weather":"不明","fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA競馬番組","_summaryOnly":True,"meetingNumber":meeting_no,"meetingDay":day_no,"netkeibaRaceId":nkid})
            if z:out.append(z)
    out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    with _jra_program_cache_lock:_jra_program_cache[iso_date]=(now,[dict(x) for x in out])
    return out

def _jra_program_lookup(iso_date:str,track:str,race_no:int):
    for r in _jra_program_summaries(iso_date):
        if str(r.get("track"))==str(track) and int(r.get("raceNumber") or 0)==int(race_no):return dict(r)
    return None

def _jra_find_cname(iso_date:str,track:str,race_no:int)->str:
    key=(iso_date,track,int(race_no))
    with _jra_cname_lookup_lock:
        if key in _jra_cname_lookup:return _jra_cname_lookup[key]
    token=iso_date.replace("-","")
    try:home=_jra_request("https://www.jra.go.jp/",None,60)
    except Exception:return ""
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        c=_jra_norm_cname(c)
        if token in c and c not in seeds:seeds.append(c)
    candidates=list(seeds)
    def live_first(items):
        # JRA exposes a basic card (pw01dde01...) and the live/full card
        # (pw01dde10...). The live/full variant carries current odds + body weight.
        return sorted(items,key=lambda c:(0 if "pw01dde10" in c else 1,0 if token in c else 1,c))
    for seed in seeds[:8]:
        try:page=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,30)
        except Exception:continue
        for c in JRA_CNAME_RE.findall(page):
            c=_jra_norm_cname(c)
            if token in c and c not in candidates:candidates.append(c)
        for c in live_first(candidates):
            if _jra_track_from_cname(c)==track and _jra_race_no_from_cname(c)==int(race_no):
                with _jra_cname_lookup_lock:_jra_cname_lookup[key]=c
                return c
    for c in live_first(candidates):
        if _jra_track_from_cname(c)==track and _jra_race_no_from_cname(c)==int(race_no):
            with _jra_cname_lookup_lock:_jra_cname_lookup[key]=c
            return c
    return ""

def _jra_text(tag) -> str:
    return re.sub(r"\s+"," ",tag.get_text(" ",strip=True) if tag else "").strip()

def _jra_iso_date(y:int,m:int,d:int)->str:
    return f"{y:04d}-{m:02d}-{d:02d}"

def _jra_date_from_cname(cname:str)->str:
    m=re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$",cname or "")
    if not m:return ""
    x=m.group(1);return f"{x[:4]}-{x[4:6]}-{x[6:8]}"

def _jra_race_no_from_cname(cname:str)->int:
    m=re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "")
    return int(m.group(1)) if m else 0

def _jra_track_from_cname(cname:str)->str:
    m=re.search(r"pw01dde(?:01|10)(\d{2})",cname or "")
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""

def _jra_parse_time_seconds(txt:str)->float:
    m=re.search(r"(?<!\d)(\d{1,2}):(\d{2}\.\d)(?!\d)",txt or "")
    if not m:return 0.0
    return int(m.group(1))*60+float(m.group(2))

def _jra_parse_past_cell(cell, cutoff:str) -> dict | None:
    txt=_jra_text(cell)
    dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",txt)
    if not dm:return None
    iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
    if cutoff and iso>=cutoff:return None
    track=""
    for t in list(JRA_TRACK_CODES.values())+["門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"]:
        if re.search(r"(?:日|\s)"+re.escape(t)+r"(?:\s|$)",txt): track=t;break
    finish=0
    fm=re.search(r"(?<!\d)(\d{1,2})\s*着(?!\d)",txt)
    if fm: finish=int(fm.group(1))
    field=0
    fsm=re.search(r"(\d{1,2})\s*頭",txt)
    if fsm: field=int(fsm.group(1))
    dist=0; surface=""
    dsm=re.search(r"(\d{3,4})(芝|ダ|障)",txt)
    if dsm: dist=int(dsm.group(1)); surface=dsm.group(2)
    cond="不明"
    for c in ["不良","稍重","重","良"]:
        if c in txt: cond=c;break
    weight=0.0
    wm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",txt)
    if wm: weight=float(wm.group(1))
    corners=[]
    for li in cell.find_all("li"):
        z=_jra_text(li)
        if re.fullmatch(r"\d{1,2}",z): corners.append(int(z))
    result_cname=_jra_attr_cname(cell,JRA_RESULT_CNAME_RE)
    rid=("jraresult-"+base64.urlsafe_b64encode(result_cname.encode()).decode().rstrip("=")) if result_cname else ""
    # title is best-effort: text between track and class/finish data
    title=""
    if track:
        after=txt.split(track,1)[1].strip()
        after=re.split(r"\s+(?:\d{1,2}着|\d{1,2}頭|\d+番)",after,1)[0]
        title=after[:60].strip()
    tm=_jra_parse_time_seconds(txt)
    return {"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":weight,"raceId":rid,"source":"JRA公式"}

def _jra_profile_runs(cname:str, cutoff:str, limit:int=5)->list[dict]:
    if not cname:return []
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessU.html",cname,86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr"))
        if "年月日" not in head or "レース名" not in head: continue
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<8: continue
            vals=[_jra_text(c) for c in cells]
            dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",vals[0])
            if not dm:continue
            iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
            if cutoff and iso>=cutoff:continue
            track=vals[1]
            title=vals[2]
            disttxt=vals[3]
            dsm=re.search(r"(芝|ダ|障)(\d{3,4})",disttxt)
            surface=dsm.group(1) if dsm else ""; dist=int(dsm.group(2)) if dsm else 0
            cond=vals[4] if len(vals)>4 else "不明"
            field=_int(vals[5]) if len(vals)>5 else 0
            finish=_int(vals[7]) if len(vals)>7 else 0
            jockey=vals[8] if len(vals)>8 else ""
            cw=float(re.sub(r"[^0-9.]","",vals[9]) or 0) if len(vals)>9 else 0
            tm=_jra_parse_time_seconds(vals[11] if len(vals)>11 else "")
            rc=_jra_attr_cname(tr,JRA_RESULT_CNAME_RE)
            rid=("jraresult-"+base64.urlsafe_b64encode(rc.encode()).decode().rstrip("=")) if rc else ""
            out.append({"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond or "不明","weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":[],"carriedWeight":cw,"jockey":jockey,"raceId":rid,"source":"JRA公式競走馬情報"})
            if len(out)>=limit:return out
    return out

def _jra_merge_run_fields(base:dict,incoming:dict)->dict:
    """Merge duplicate starts field-by-field instead of discarding richer data."""
    out=dict(base or {})
    for key,value in (incoming or {}).items():
        if not _jra_run_value_present(key,out.get(key)) and _jra_run_value_present(key,value):out[key]=value
        elif key=="cornerPositions" and value and len(value)>len(out.get(key) or []):out[key]=value
    sources=[]
    for src in (str((base or {}).get("source") or ""),str((incoming or {}).get("source") or "")):
        if src and src not in sources:sources.append(src)
    if sources:out["source"]=" + ".join(sources)
    return out


def _jra_run_core_complete(r:dict)->bool:
    try:finish=int(r.get("finish") or 0);field=int(r.get("fieldSize") or 0);distance=int(r.get("distance") or 0)
    except (TypeError,ValueError):return False
    return bool(str(r.get("date") or "") and str(r.get("track") or "") and finish>0 and field>1 and distance>0)


def _jra_history_complete(runs:list[dict],career_complete:bool=False)->bool:
    rows=[r for r in (runs or []) if isinstance(r,dict)]
    target=min(5,len(rows)) if career_complete else 5
    if target==0:return bool(career_complete)
    return len(rows)>=target and sum(1 for r in rows[:target] if _jra_run_core_complete(r))>=target


def _jra_merge_runs(a:list[dict],b:list[dict],limit:int=5)->list[dict]:
    merged={};order=[]
    for r in list(a or [])+list(b or []):
        if not isinstance(r,dict):continue
        key=_jra_run_key(r)
        if key not in merged:
            merged[key]=dict(r);order.append(key)
        else:merged[key]=_jra_merge_run_fields(merged[key],r)
    allr=[merged[k] for k in order]
    allr.sort(key=lambda r:str(r.get("date") or ""),reverse=True)
    return allr[:limit]

def _jra_parse_race(cname:str, supplement_profiles: bool = True)->dict|None:
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    cache_sec=int(os.getenv("JRA_LIVE_ODDS_CACHE_SEC","45")) if date==_today_iso() else 600
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    # The basic dde01 card can omit live fields even while the official dde10
    # card for the same race already contains them. Prefer the official live card.
    if date==_today_iso() and "pw01dde10" not in cname:
        live=[]
        for cc in JRA_CNAME_RE.findall(html):
            cc=_jra_norm_cname(cc)
            if ("pw01dde10" in cc and _jra_date_from_cname(cc)==date and
                _jra_track_from_cname(cc)==track and _jra_race_no_from_cname(cc)==race_no):
                live.append(cc)
        if live:
            cname=live[0]
            try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,0)
            except Exception:pass
    soup=BeautifulSoup(html,"html.parser")
    full=_jra_text(soup)
    if not date or not track or not race_no:return None
    sm=re.search(r"発走時刻[：:]\s*(\d{1,2})時(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else 0
    course_desc=dm.group(2) if dm else ""
    surface="芝" if "芝" in course_desc else ("ダート" if "ダート" in course_desc else ("障害" if "障" in course_desc else ""))
    weather="不明"; condition="不明"
    wm=re.search(r"天候\s*([^\s]+)",full)
    if wm:weather=wm.group(1)[:4]
    cm=re.search(r"(?:芝|ダート)\s*(良|稍重|重|不良)",full)
    if cm:condition=cm.group(1)
    title=""
    title_block=JRA_BAD_TITLE_RE
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if not tx or len(tx)>=80 or title_block.search(tx) or "出馬表" in tx:
            continue
        if re.match(r"^\d+レース$",tx):
            continue
        title=tx;break
    if not title:title=f"{race_no}R"
    prize1=0
    pm=re.search(r"1着\s*([\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except:pass
    horses=[]
    target_table=None
    for table in soup.find_all("table"):
        tx=_jra_text(table.find("thead") or table)
        if "馬番" in tx and "前走" in tx:
            target_table=table;break
    if not target_table:return None
    for tr in target_table.find_all("tr"):
        cells=tr.find_all(["th","td"])
        if len(cells)<4:continue
        # horse number among first 3 cells
        no=0; noidx=-1
        for ci,c in enumerate(cells[:3]):
            mt=re.fullmatch(r"\s*(\d{1,2})\s*",_jra_text(c))
            if mt and 1<=int(mt.group(1))<=18:
                no=int(mt.group(1));noidx=ci;break
        if not no:continue
        frame_no=0
        fm=re.search(r"枠\s*(\d)",_jra_text(cells[0])+" "+str(cells[0]))
        if fm:frame_no=int(fm.group(1))
        # identify horse info and profile cells
        info=None; profile=None; horse_cname=""
        for c in cells:
            hc=_jra_attr_cname(c,JRA_HORSE_CNAME_RE)
            if hc:
                info=c;horse_cname=hc;break
        if info is None:
            info=cells[min(len(cells)-1,noidx+1)]
        info_i=cells.index(info)
        profile=cells[info_i+1] if info_i+1<len(cells) else None
        # horse name from horse profile link or first plausible link/text
        name=""
        for a in info.find_all("a"):
            if _jra_attr_cname(a,JRA_HORSE_CNAME_RE):
                name=_jra_text(a);break
        if not name:
            name=re.split(r"\d+(?:\.\d+)?\(?",_jra_text(info),1)[0].strip()[:40]
        if not name:continue
        infot=_jra_text(info); prot=_jra_text(profile)
        sex="";age=0
        sx=re.search(r"(牡|牝|せん)(\d+)",prot)
        if sx:sex=sx.group(1);age=int(sx.group(2))
        cw=0.0
        cwm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",prot)
        if cwm:cw=float(cwm.group(1))
        jockey=""
        links=[_jra_text(a) for a in profile.find_all("a")] if profile else []
        if links:jockey=links[-1]
        if not jockey and cwm:
            jockey=prot[cwm.end():].strip().split(" ")[0:3]
            jockey=" ".join(jockey).strip()
        trainer=""
        tm=re.search(r"([^\s]+(?:\s[^\s]+)?)\((?:美浦|栗東|本会外)\)",infot)
        if tm:trainer=tm.group(1).strip()
        prize=0
        prm=re.search(r"([\d,.]+)万円",infot)
        if prm:
            try:prize=int(float(prm.group(1).replace(",",""))*10000)
            except:pass
        past=[]
        past_cells=cells[info_i+2:info_i+6]
        for c in past_cells:
            rr=_jra_parse_past_cell(c,date)
            if rr:past.append(rr)
        # JRA card exposes 前走〜4走前. If all four slots were inspected and fewer
        # than four real runs exist, that is the horse's full career to date.
        career_complete=(len(past_cells)>=4 and len(past)<4)
        win_odds=0.0; popularity=0; body_weight=0; body_change=None
        tail=infot.split(name,1)[1] if name in infot else infot
        om=re.search(r"([0-9]+(?:\.[0-9]+)?)\s*\((\d+)番人気\)",tail)
        if om:
            try: win_odds=float(om.group(1)); popularity=int(om.group(2))
            except: pass
        bwm=re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]",infot)
        if bwm:
            try: body_weight=int(bwm.group(1)); body_change=int(bwm.group(2))
            except: pass
        elif re.search(r"(\d{3})\s*kg",infot):
            try: body_weight=int(re.search(r"(\d{3})\s*kg",infot).group(1))
            except: pass
        scratch_status=_scratch_status(_jra_text(tr))
        horses.append({"horseNumber":no,"frameNumber":frame_no,"name":name,"age":age,"sex":sex,"carriedWeight":cw,"jockey":jockey,"trainer":trainer,"prizeMoneyAtRace":prize,"recentRaces":past,"winOdds":win_odds or None,"popularity":popularity or None,"bodyWeight":body_weight or None,"bodyWeightChange":body_change,"oddsSource":"JRA公式" if win_odds else "","status":scratch_status,"scratched":bool(scratch_status),"_jraHorseCname":horse_cname,"_jraCareerComplete":career_complete,"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}})
    if not horses:return None
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    # Listing must stay fast. Full five-run profile supplementation is done only when needed.
    if supplement_profiles:
        def supplement(h):
            existing=h.get("recentRaces") or []
            if _jra_history_complete(existing,bool(h.get("_jraCareerComplete"))):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(existing,extra,5)
            return h
        workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            horses=list(pool.map(supplement,horses))
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(horses),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"horses":horses,"source":"JRA公式","jraCname":cname})

def _jra_parse_race_summary(cname:str)->dict|None:
    """Fast list-page parser: no horse/profile parsing. Full card loads only when opened."""
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    if not date or not track or not race_no:return None
    cache_sec=45 if date==_today_iso() else 900
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    soup=BeautifulSoup(html,"html.parser"); full=_jra_text(soup)
    sm=re.search(r"発走時刻\s*[：:]?\s*(\d{1,2})時\s*(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else 0; desc=dm.group(2) if dm else ""
    surface="芝" if "芝" in desc else ("ダート" if "ダート" in desc else ("障害" if "障" in desc else ""))
    weather="不明"; condition="不明"
    wm=re.search(r"天候\s*([^\s]+)",full)
    if wm:weather=wm.group(1)[:4]
    cm=re.search(r"(?:芝|ダート)\s*(良|稍重|重|不良)",full)
    if cm:condition=cm.group(1)
    blocked=JRA_BAD_TITLE_RE
    title=""
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if not tx or len(tx)>=80 or blocked.search(tx) or "出馬表" in tx or re.match(r"^\d+レース$",tx):continue
        title=tx;break
    if not title:title=f"{race_no}R"
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA公式・高速一覧","jraCname":cname,"_summaryOnly":True})

def fetch_jra_official(iso_date:str, lightweight: bool = False)->list[dict]:
    if lightweight:return _jra_program_summaries(iso_date)
    token=iso_date.replace("-","")
    try:
        home=_jra_request("https://www.jra.go.jp/",None,120)
    except Exception:
        return []
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        if token in c and c not in seeds:
            seeds.append(c)
    if not seeds:
        return []

    # v48: a race page contains links to the other active venue(s) too.
    # v47 filtered those links to the first venue, which could leave only Nakayama.
    # Discover one seed per track first, then expand each venue to all race-number links.
    track_seed={}
    for c in seeds:
        tr=_jra_track_from_cname(c)
        if tr and tr not in track_seed:
            track_seed[tr]=c

    discovered=[]
    processed_tracks=set()
    queue=list(track_seed.items())
    guard=0
    while queue and guard<12:
        guard+=1
        track,seed=queue.pop(0)
        if track in processed_tracks:
            continue
        processed_tracks.add(track)
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,180)
        except Exception:
            continue
        links=[]
        for c in JRA_CNAME_RE.findall(html):
            if token not in c:
                continue
            if c not in links:
                links.append(c)
            if c not in discovered:
                discovered.append(c)
        # Important: do NOT restrict to the current track. Any newly linked venue
        # becomes a seed and is expanded on its own page.
        for c in links:
            tr=_jra_track_from_cname(c)
            if tr and tr not in processed_tracks and all(q[0]!=tr for q in queue):
                queue.append((tr,c))

    for c in seeds:
        if c not in discovered:
            discovered.append(c)

    # prefer detailed 01 variant and deduplicate by venue/race number
    chosen={}
    for c in discovered:
        key=(_jra_track_from_cname(c),_jra_race_no_from_cname(c))
        if not key[0] or not key[1]:
            continue
        if key not in chosen or c.startswith("pw01dde01"):
            chosen[key]=c

    def one(c):
        try:
            return _jra_parse_race_summary(c) if lightweight else _jra_parse_race(c, supplement_profiles=True)
        except Exception as exc:
            print("JRA official race parse failed",c,exc)
            return None
    workers=max(4,min(16,int(os.getenv("JRA_SUMMARY_WORKERS","12") if lightweight else os.getenv("JRA_RACE_WORKERS","6"))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        races=[x for x in pool.map(one,chosen.values()) if x]
    races.sort(key=lambda r:(r.get("track") or "",int(r.get("raceNumber") or 0)))
    return races

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


_nar_sync_io_lock = threading.Lock()
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

def _race_minutes(row:dict)->int:
    s=str(row.get("startTime") or "")
    m=re.match(r"^(\d{1,2}):(\d{2})$",s)
    return int(m.group(1))*60+int(m.group(2)) if m else 9999

def _commercial_target_rows(rows:list[dict], now_min:int)->list[dict]:
    """Commercial mode prepares the whole day; upcoming races are simply first."""
    valid=[r for r in rows if r.get("id") and r.get("track")]
    valid.sort(key=lambda r:(
        0 if _race_minutes(r)>=now_min-25 else 1,
        abs(_race_minutes(r)-now_min),
        str(r.get("track") or ""),
        int(r.get("raceNumber") or 0),
    ))
    seen=set();out=[]
    for r in valid:
        rid=str(r.get("id") or "")
        if rid and rid not in seen:
            seen.add(rid);out.append(r)
    return out


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


_race_history_lock = threading.Lock()
_race_history_jobs: dict[str, dict] = {}

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
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        cov = _history_counts(horse_names, iso_date)
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"","source":"NAR公式月次レースデータ"}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        months = list(_months_from_race_date(iso_date, max_months))
        wave = max(2, min(4, int(os.getenv("NAR_ON_DEMAND_WAVE_MONTHS", "3"))))
        try:
            for pos in range(0, len(months), wave):
                batch = months[pos:pos+wave]
                _, errs = _sync_nar_month_wave(batch)
                errors.extend(errs)
                months_done += len(batch)
                cov_now = _history_counts(horse_names, iso_date)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"NAR公式 高速並列履歴"}
                if _history_is_enough(cov_now, months_done):
                    break
            cov_now = _history_counts(horse_names, iso_date)
            # v155: if official NAR history is still under five starts, search a second
            # career source. This is especially important for JRA/NAR transfers.
            supplemented=0
            under=list(cov_now.get("underFive") or [])
            if under:
                try:supplemented=_supplement_sparse_nar_history(race_id,under,iso_date)
                except Exception as exc:errors.append("netkeiba DB補完:"+str(exc))
            status = "done" if (cov_now.get("horsesWithHistory",0) > 0 or supplemented>0) else ("error" if errors else "done")
            source="NAR公式 高速並列履歴"+(" + netkeiba DB補完" if supplemented else "")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,"coverage":cov_now,"error":" | ".join(errors[-5:]),"source":source,"supplementedHorses":supplemented}
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
    if not DB_PATH.exists():
        return []
    conn = _new_conn(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT r.*,
                   COUNT(e.horse_no) AS entry_count,
                   SUM(CASE WHEN e.finish=1 THEN 1 ELSE 0 END) AS f1,
                   SUM(CASE WHEN e.finish=2 THEN 1 ELSE 0 END) AS f2,
                   SUM(CASE WHEN e.finish=3 THEN 1 ELSE 0 END) AS f3
            FROM races r
            LEFT JOIN entries e ON e.track=r.track AND e.date=r.date AND e.race_no=r.race_no
            WHERE r.date=?
            GROUP BY r.track,r.date,r.race_no
            ORDER BY r.track,r.race_no
            """,
            (iso_date,),
        ).fetchall()
        out=[]
        for r in rows:
            count=int(r["entry_count"] or r["field_size"] or 0)
            finalized=count>0 and int(r["f1"] or 0)>0 and int(r["f2"] or 0)>0 and (count<3 or int(r["f3"] or 0)>0)
            out.append({
                "id":f"nar-{iso_date}-{r['track']}-{int(r['race_no']):02d}",
                "circuit":"地方","date":iso_date,"track":r["track"],"raceNumber":int(r["race_no"]),
                "title":r["title"] or f"{int(r['race_no'])}R","distance":int(r["distance"] or 0),
                "condition":r["condition"] or "不明","weather":r["weather"] or "不明",
                "fieldSize":count,"racePrize1":int(r["prize1"] or 0),"surface":"",
                "startTime":r["start_time"] or "","scheduledStartTime":r["scheduled_start_time"] or r["start_time"] or "",
                "startTimeChanged":bool((r["scheduled_start_time"] or "") and (r["start_time"] or "") and r["scheduled_start_time"]!=r["start_time"]),
                "horses":[],"result":{"status":"確定","finishers":[{"finish":1}]} if finalized else None,"source":"NAR公式"
            })
        return out
    finally:
        conn.close()



NETKEIBA_TRACK_CODES={"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
_netkeiba_cache_lock=threading.Lock(); _netkeiba_cache={}

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

def _netkeiba_db_horse_history(name:str, cutoff:str, limit:int=5)->dict:
    """Fallback career lookup by horse name for sparse NAR histories.

    Uses netkeiba DB only as a supplement after NAR official history has been searched.
    The result page contains both central and local starts, which is useful for transfers.
    """
    name=_clean(name)
    if not name:return {"name":"","recentRaces":[]}
    try:
        # netkeiba expects EUC-JP query bytes; UTF-8 silently returns no hits.
        from arvexq.databanks.netkeiba_career import search_url, parse_search
        html=_netkeiba_get(search_url(name),float(os.getenv("NETKEIBA_DB_SEARCH_TIMEOUT_SEC","4.0")),86400)
    except Exception as exc:
        print("netkeiba DB horse search failed",name,exc);return {"name":name,"recentRaces":[]}
    # Exact-name candidates only (absolute links, or a direct redirect to the horse page).
    candidates=[c["id"] for c in parse_search(html,name)]
    best={"name":name,"recentRaces":[]};best_score=-1
    for hid in candidates[:4]:
        try:
            page=_netkeiba_get(f"https://db.netkeiba.com/horse/result/{hid}/",float(os.getenv("NETKEIBA_DB_RESULT_TIMEOUT_SEC","4.0")),86400)
        except Exception as exc:
            print("netkeiba DB horse result failed",name,hid,exc);continue
        ps=BeautifulSoup(page,"html.parser");runs=[]
        for table in ps.find_all("table"):
            trs=table.find_all("tr")
            if not trs:continue
            header_cells=trs[0].find_all(["th","td"])
            headers=[_clean(c.get_text(" ",strip=True)) for c in header_cells]
            # Headers are rendered with spaces ("着 順", "頭 数").
            joined="|".join(re.sub(r"\s+","",h) for h in headers)
            if "日付" not in joined or "着順" not in joined or "距離" not in joined:continue
            def hidx(*keys):
                for i,h in enumerate(headers):
                    hh=re.sub(r"\s+","",h)
                    if any(k in hh for k in keys):return i
                return -1
            i_date=hidx("日付");i_track=hidx("開催");i_title=hidx("レース名");i_field=hidx("頭数")
            i_fin=hidx("着順");i_jockey=hidx("騎手");i_cw=hidx("斤量");i_dist=hidx("距離")
            i_cond=hidx("馬場");i_time=hidx("タイム");i_corner=hidx("通過");i_bw=hidx("馬体重")
            for tr in trs[1:]:
                cells=tr.find_all(["th","td"])
                vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
                def val(i):return vals[i] if i>=0 and i<len(vals) else ""
                dm=re.search(r"(20\d{2})[./](\d{1,2})[./](\d{1,2})",val(i_date))
                if not dm:continue
                date=f"{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
                if cutoff and date>=cutoff:continue
                fm=re.match(r"\s*(\d+)",val(i_fin))
                if not fm:continue
                dist_txt=val(i_dist);dst=re.search(r"(芝|ダ|障)[^0-9]*(\d{3,4})",dist_txt)
                if not dst:continue
                track=re.sub(r"^\d+|\d+$","",val(i_track)).strip()
                field=_safe_int(val(i_field));corn=[]
                cm=re.search(r"\d{1,2}(?:-\d{1,2})+",val(i_corner))
                if cm:corn=[int(x) for x in cm.group(0).split("-")]
                tm=0.0;mt=re.search(r"(?:(\d+):)?(\d{1,2})\.(\d)",val(i_time))
                if mt:tm=int(mt.group(1) or 0)*60+int(mt.group(2))+int(mt.group(3))/10
                bwm=re.search(r"(\d{3,4})(?:\s*\(\s*([+\-]?\d+)\s*\))?",val(i_bw))
                runs.append({
                    "date":date,"track":track,"title":val(i_title),"distance":int(dst.group(2)),
                    "surface":"障害" if dst.group(1)=="障" else ("芝" if dst.group(1)=="芝" else "ダート"),
                    "condition":val(i_cond) or "不明","weather":"不明","fieldSize":field,
                    "finish":int(fm.group(1)),"timeSeconds":tm,"cornerPositions":corn,
                    "carriedWeight":float(re.search(r"\d+(?:\.\d+)?",val(i_cw)).group()) if re.search(r"\d+(?:\.\d+)?",val(i_cw)) else 0.0,
                    "bodyWeight":int(bwm.group(1)) if bwm else None,
                    "bodyWeightChange":int(bwm.group(2)) if bwm and bwm.group(2) is not None else None,
                    "jockey":val(i_jockey),"source":"netkeiba DB補完",
                })
                if len(runs)>=limit:break
            if runs:break
        runs=sorted(runs,key=lambda z:str(z.get("date") or ""),reverse=True)[:limit]
        # Same-name horses: the current runner is the one with the latest pre-race
        # start, not a retired namesake with a longer record.
        score=(int(runs[0]["date"].replace("-","")) if runs else 0)*1000 + len(runs)
        if score>best_score:
            best_score=score;best={"name":name,"_netkeibaHorseId":hid,"recentRaces":runs,"source":"netkeiba DB補完"}
    return best


def _supplement_sparse_nar_history(race_id:str, names:list[str], cutoff:str)->int:
    if not names:return 0
    unique=list(dict.fromkeys([_clean(x) for x in names if _clean(x)]))
    workers=max(2,min(4,int(os.getenv("NETKEIBA_DB_HISTORY_WORKERS","4"))))
    rows=[]
    with ThreadPoolExecutor(max_workers=min(workers,len(unique))) as pool:
        futs={pool.submit(_netkeiba_db_horse_history,name,cutoff,5):name for name in unique}
        for fut in as_completed(futs):
            try:
                z=fut.result() or {}
                if z.get("recentRaces"):rows.append(z)
            except Exception as exc:print("sparse NAR history supplement failed",futs[fut],exc)
    if not rows:return 0
    try:
        with _enrich_data_lock:
            olddata=_enrich_data.get(race_id) or {}
            merged={}
            for rr in (olddata.get("netkeibaRows") or [])+rows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                if key:merged[key]=rr
            _enrich_data[race_id]={
                "netkeibaRows":list(merged.values()),
                "smartRows":olddata.get("smartRows") or [],
                "extra":olddata.get("extra") or [],
            }
        with _enrich_jobs_lock:
            prev=_enrich_jobs.get(race_id) or {}
            src=list(prev.get("sources") or [])
            if "netkeiba DB補完" not in src:src.append("netkeiba DB補完")
            _enrich_jobs[race_id]={**prev,"status":"done","sources":src,"finishedAt":time.time()}
    except Exception as exc:
        print("sparse NAR enrichment cache failed",race_id,exc);return 0
    return len(rows)


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

def _parse_recent_cell(txt:str)->dict|None:
    s=_clean(txt)
    md=re.search(r"(20\d{2})[./](\d{1,2})[./](\d{1,2})\s*([^\s]+)\s+(\d+)\s+(.+?)\s+((?:芝|ダ|障)[^0-9 ]*)(\d{3,4})",s)
    if not md:return None
    date=f"{int(md.group(1)):04d}-{int(md.group(2)):02d}-{int(md.group(3)):02d}";track=md.group(4);finish=int(md.group(5));title=_clean(md.group(6));distance=int(md.group(8));surface=md.group(7)
    tm=0.0;mt=re.search(r"\b(\d+):(\d{2}\.\d)\b",s)
    if mt:tm=int(mt.group(1))*60+float(mt.group(2))
    cond="不明";mc=re.search(r"(?:^|\s)(良|稍|重|不)(?:\s|$)",s)
    if mc:cond=mc.group(1)
    field=0;mf=re.search(r"(\d+)頭",s);field=int(mf.group(1)) if mf else 0
    corners=[]
    for cm in re.findall(r"(?<!\d)(\d{1,2}(?:-\d{1,2}){1,3})(?!\d)",s):
        vals=[int(x) for x in cm.split("-")]
        if vals and max(vals)<=(field if field else 30):
            corners=vals;break
    # 斤量は「通過順」の直前にある。単純に最初の2桁を拾うと着順(10〜18)や
    # 頭数を誤って斤量にしてしまうため、通過順の直前を優先して探す。
    cw=0.0;mw=re.search(r"(?<!\d)(\d{2}(?:\.\d)?)\s+(?=\d{1,2}(?:-\d{1,2}){1,3}(?!\d))",s)
    if not mw:mw=re.search(r"(?<!\d)(5[0-9](?:\.\d)?)(?!\d)",s)
    if not mw:mw=re.search(r"\s(\d{2}(?:\.\d)?)\s",s)
    if mw:
        try:cw=float(mw.group(1))
        except Exception:pass
    return {"date":date,"track":track,"title":title,"distance":distance,"surface":"障害" if surface.startswith("障") else ("芝" if surface.startswith("芝") else "ダート"),"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":cw,"source":"netkeiba"}

_NK_WAKU_RE = re.compile(r"^Waku(\d)$")
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\d{1,2})$")
_NK_SEXAGE_RE = re.compile(r"^(牡|牝|セ|騸)\s*(\d{1,2})")


def _nk_row_horse_no(tr, index: int | None = None) -> int:
    """netkeiba HorseList 行の馬番。

    現行DOMは馬番セルが無く、オッズ span の id (odds-1_01) と行順が馬番を持つ。
    旧DOMは td.Umaban に馬番があったため両対応にする。
    """
    o = tr.find("span", id=_NK_ODDS_ID_RE)
    if o is not None:
        m = _NK_ODDS_ID_RE.match(str(o.get("id") or ""))
        if m and int(m.group(1)) > 0:
            return int(m.group(1))
    um = tr.find("td", class_=re.compile(r"^Umaban"))
    if um is not None:
        m = re.search(r"\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and int(m.group()) > 0:
            return int(m.group())
    if index is not None:
        return int(index) + 1
    return 0


def _nk_row_frame(tr) -> int:
    for td in tr.find_all("td"):
        for cls in (td.get("class") or []):
            m = _NK_WAKU_RE.match(str(cls))
            if m:
                return int(m.group(1))
    return 0


def _nk_row_horse(tr, index: int | None = None) -> dict | None:
    """netkeiba HorseList 1行 -> 出走馬 dict。旧DOM/新DOM両対応。"""
    info = tr.select_one("td.Horse_Info") or tr.select_one("td.HorseInfo")
    if info is None:
        return None
    name_a = (info.select_one("dt.Horse a") or info.select_one("div.Horse02 a")
              or info.select_one("dt a") or info.select_one(".HorseName a"))
    name = _clean(name_a.get_text(" ", strip=True)) if name_a else ""
    if not name or "のデータベース" in name or len(name) > 24:
        return None
    no = _nk_row_horse_no(tr, index)
    if no <= 0:
        return None

    sex = ""; age = 0
    barei = _clean(tr.select_one("span.Barei").get_text(" ", strip=True)) if tr.select_one("span.Barei") else ""
    if not barei:
        bt = tr.select_one("td.Barei")
        barei = _clean(bt.get_text(" ", strip=True)) if bt else ""
    if not barei:
        dd_age = info.select_one("dd.Age")
        if dd_age is not None:
            barei = _clean(dd_age.get_text(" ", strip=True))
    m = _NK_SEXAGE_RE.match(barei)
    if m:
        sex = m.group(1); age = int(m.group(2))

    jockey = ""; carried = 0.0
    dd_j = info.select_one("dd.Jockey")
    if dd_j is not None:
        em = dd_j.find("em")
        jockey = _clean(em.get_text(" ", strip=True)) if em else ""
        jtxt = _clean(dd_j.get_text(" ", strip=True))
        if not jockey:
            jockey = _clean(re.sub(r"[\d.]+", " ", jtxt))
        m = re.search(r"(\d{2}(?:\.\d)?)\s*$", jtxt)
        if m:
            try: carried = float(m.group(1))
            except Exception: carried = 0.0
    if not jockey or not carried:
        jt = tr.select_one("td.Jockey")
        if jt is not None:
            ja = jt.find("a")
            if ja is not None and not jockey:
                jockey = _clean(ja.get_text(" ", strip=True))
            jtxt = _clean(jt.get_text(" ", strip=True))
            m = re.search(r"(\d{2}(?:\.\d)?)\s*$", jtxt)
            if m and not carried:
                try: carried = float(m.group(1))
                except Exception: carried = 0.0

    trainer = ""
    tr_el = tr.select_one("td.Trainer")
    if tr_el is not None:
        trainer = _clean(tr_el.get_text(" ", strip=True))
    if not trainer:
        for sel in ("div.Horse05 a", "div.Horse05"):
            el = info.select_one(sel)
            if el is None:
                continue
            t = re.sub(r"^(栗東|美浦|地方|外国)\s*[・･]\s*", "", _clean(el.get_text(" ", strip=True)))
            if t:
                trainer = t
                break

    wtxt = ""
    wt = tr.select_one("td.Weight")
    if wt is not None:
        wtxt = _clean(wt.get_text(" ", strip=True))
    if not wtxt:
        wt = info.select_one("div.Weight")
        if wt is not None:
            wtxt = _clean(wt.get_text(" ", strip=True))
    bw = None; chg = None
    m = re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?", wtxt)
    if m:
        try:
            bw = int(m.group(1))
            chg = int(m.group(2)) if m.group(2) is not None else None
        except Exception:
            bw = None; chg = None

    odds = None; pop = None
    o = tr.find("span", id=re.compile(r"^odds-1_"))
    if o is not None:
        m = re.search(r"\d+(?:\.\d+)?", _clean(o.get_text(" ", strip=True)))
        if m:
            try: odds = float(m.group())
            except Exception: odds = None
    p = tr.find("span", id=re.compile(r"^ninki-1_"))
    if p is not None:
        m = re.search(r"\d+", _clean(p.get_text(" ", strip=True)))
        if m: pop = int(m.group())

    txt = _clean(tr.get_text(" ", strip=True))
    status = _scratch_status(txt)
    return {
        "horseNumber": no,
        "frameNumber": _nk_row_frame(tr) or int((no + 1) // 2),
        "name": name, "sex": sex, "age": age,
        "carriedWeight": carried, "jockey": jockey, "trainer": trainer,
        "bodyWeight": bw, "bodyWeightChange": chg,
        "winOdds": odds, "popularity": pop,
        "status": status, "scratched": bool(status),
        "recentRaces": [],
        "jockeyStats": {}, "trainerStats": {}, "jockeyProfile": {}, "trainerProfile": {},
        "source": "netkeiba",
    }




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

def central_race_summaries(iso_date: str, allow_network: bool = False, force: bool = False) -> list[dict]:
    db=[]
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            rows=conn.execute("SELECT payload FROM central_races WHERE date=? ORDER BY track,race_no",(iso_date,)).fetchall()
            for x in rows:
                try:r=json.loads(x["payload"])
                except Exception:continue
                hs=r.get("horses") if isinstance(r.get("horses"),list) else [];q=dict(r);q["fieldSize"]=int(q.get("fieldSize") or len(hs));q["horses"]=[]
                if JRA_BAD_TITLE_RE.search(str(q.get("title") or "")):q["title"]=f"{int(q.get('raceNumber') or 0)}R"
                res=q.get("result") if isinstance(q.get("result"),dict) else None
                if res and (res.get("finishers") or res.get("status")=="確定"):q["result"]={"status":res.get("status") or "確定","finishers":res.get("finishers") or [{"finish":1}]}
                else:q["result"]=None
                db.append(q)
        finally:conn.close()
    valid=[x for x in db if not JRA_BAD_TITLE_RE.search(str(x.get("title") or "")) and int(x.get("distance") or 0)>0]
    merged={(str(r.get("track") or ""),int(r.get("raceNumber") or 0)):dict(r) for r in valid}
    tracks={k[0] for k in merged if k[0]}
    # A normal JRA day has multiple venues. If the cache is clearly complete, return instantly.
    complete=len(merged)>=20 and len(tracks)>=2
    if allow_network and (force or not complete):
        program=[]; nk=[]
        try:program=_jra_program_summaries(iso_date)
        except Exception as exc:print("JRA program list failed",iso_date,exc)
        # Program page is the fast authoritative schedule. Netkeiba fills gaps and provides race ids.
        if len(program)<20 or len({str(r.get('track') or '') for r in program})<2:
            try:nk=_netkeiba_race_summaries(iso_date)
            except Exception as exc:print("netkeiba summary fallback failed",iso_date,exc)
        else:
            # Reuse netkeiba only from its short in-memory cache when available; avoid a second wait.
            try:
                token=iso_date.replace('-','');url=f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={token}"
                with _netkeiba_cache_lock:
                    hit=_netkeiba_cache.get(url)
                if hit:nk=_netkeiba_race_summaries(iso_date)
            except Exception:pass
        fresh=list(program or [])+list(nk or [])
        for r in fresh:
            key=(str(r.get("track") or ""),int(r.get("raceNumber") or 0))
            if not key[0] or not key[1]:continue
            old=merged.get(key,{})
            z=dict(old)
            # Keep rich cached horses/result, but replace stale schedule fields with fresh schedule data.
            for k,v in r.items():
                if k in {"horses","result"}:continue
                if v not in (None,"",0,[]):z[k]=v
            if old.get("result"):z["result"]=old.get("result")
            if old.get("horses"):z["horses"]=[]
            merged[key]=normalize_central_race(z) or z
        if fresh:
            try:
                st=CentralStore();st.upsert(list(merged.values()));st.conn.close()
            except Exception as exc:print("central summary cache save failed",exc)
    out=list(merged.values());out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    return out

NAR_BABA_CODES={"帯広ば":"03","帯広":"03","盛岡":"10","水沢":"11","浦和":"18","船橋":"19","大井":"20","川崎":"21","金沢":"22","笠松":"23","名古屋":"24","園田":"27","姫路":"28","高知":"31","佐賀":"32","門別":"36"}
NAR_NETKEIBA_CODES={"門別":"30","盛岡":"35","水沢":"36","浦和":"42","船橋":"43","大井":"44","川崎":"45","金沢":"46","笠松":"47","名古屋":"48","園田":"50","姫路":"51","高知":"54","佐賀":"55"}

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

_nar_odds_cache_lock=threading.Lock()
_nar_odds_cache:dict[str,tuple[float,dict]]={}

def _parse_nar_live_odds_html(html:str)->dict:
    """Parse NAR official 単・複 page across header and positional layouts."""
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    out={}

    # Header-driven layout.
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        header=[];header_idx=-1
        for ri,tr in enumerate(rows[:4]):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if any("馬番" in x for x in vals) and any("単勝" in x for x in vals):
                header=vals;header_idx=ri;break
        if not header:continue

        def idxpart(part):
            for i,x in enumerate(header):
                if part in x:return i
            return -1

        ino=idxpart("馬番");iodd=idxpart("単勝");ipop=idxpart("人気");ibw=idxpart("馬体重")
        for tr in rows[header_idx+1:]:
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if ino<0 or ino>=len(vals) or iodd<0 or iodd>=len(vals):continue
            mn=re.fullmatch(r"\D*(\d{1,2})\D*",vals[ino])
            if not mn:continue
            no=int(mn.group(1))
            om=re.search(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",vals[iodd])
            odds=float(om.group(1)) if om else 0.0
            scratch_status=_scratch_status(vals[iodd])
            pop=0
            if ipop>=0 and ipop<len(vals):
                pm=re.search(r"\d+",vals[ipop]);pop=int(pm.group()) if pm else 0
            bw=0;chg=None
            if ibw>=0 and ibw<len(vals):
                bm=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",vals[ibw])
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
            if odds<=0 and not bw and not scratch_status:
                continue
            out[no]={"winOdds":odds or None,"popularity":pop or None,"bodyWeight":bw or None,
                     "bodyWeightChange":chg,"oddsSource":"NAR公式" if odds else "NAR公式出馬表",
                     "status":scratch_status,"scratched":bool(scratch_status)}

    # Current official layout second pass:
    # 枠 | 馬番 | 馬名 | 単勝 | 複勝下限 | 複勝上限 | 性齢 | 馬体重 ...
    # Always run this pass, even when the header-driven pass already found odds.
    # NAR uses multi-row/rowspan headers and the header index can be shifted for
    # 馬体重 on only one runner. Previously `if not out` skipped this reliable
    # flat-row pass as soon as odds existed, leaving cases such as the last horse
    # with odds but bodyWeight=None. Merge the flat row into missing live fields.
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if len(vals)<4:continue
            m0=re.fullmatch(r"\d{1,2}",vals[0])
            m1=re.fullmatch(r"\d{1,2}",vals[1]) if len(vals)>1 else None
            oddm=re.fullmatch(r"\d+(?:\.\d+)?",vals[3]) if len(vals)>3 else None
            scratch_status=_scratch_status(vals[3] if len(vals)>3 else "")
            if not (m0 and m1 and (oddm or scratch_status)):continue
            no=int(m1.group());odds=float(oddm.group()) if oddm else 0.0
            if no<=0 or (odds<=0 and not scratch_status):continue
            bw=0;chg=None
            for cell in vals[6:10]:
                bm=re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?",cell)
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
                    break
            z=out.setdefault(no,{})
            if odds>0:z["winOdds"]=odds
            if bw:
                z["bodyWeight"]=bw
                z["bodyWeightChange"]=chg
            z["oddsSource"]="NAR公式" if odds else z.get("oddsSource","")
            if scratch_status:
                z["status"]=scratch_status;z["scratched"]=True
            else:
                z.setdefault("status","");z.setdefault("scratched",False)

    ranked=sorted((float(v["winOdds"]),no) for no,v in out.items() if v.get("winOdds"))
    rank=0;last=None
    for ix,(odd,no) in enumerate(ranked,1):
        if last is None or odd!=last:rank=ix
        if not out[no].get("popularity"):out[no]["popularity"]=rank
        last=odd
    return out


def _nar_live_odds(track:str,iso_date:str,race_no:int,force:bool=False)->dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code:return {}
    key=f"{code}|{iso_date}|{race_no}";now=time.time();ttl=int(os.getenv("NAR_LIVE_ODDS_CACHE_SEC","20"))
    with _nar_odds_cache_lock:
        hit=_nar_odds_cache.get(key)
        if hit and not force and now-hit[0]<ttl:return hit[1]

    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no),"t":int(time.time()*1000) if force else ""})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/OddsTanFuku_ipat?"+q,
    ]
    out={}
    for url in urls:
        req=urllib.request.Request(url,headers={
            "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
            "Accept-Language":"ja-JP,ja;q=0.9",
            "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
        })
        try:
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_ODDS_TIMEOUT_SEC","2.5"))) as res:
                html=_jra_decode(res.read())
            out=_parse_nar_live_odds_html(html)
            if out:break
        except Exception as exc:
            print("NAR odds fetch failed",track,iso_date,race_no,url,exc)

    with _nar_odds_cache_lock:
        _nar_odds_cache[key]=(now,out)
        if len(_nar_odds_cache)>64:
            oldest=min(_nar_odds_cache.items(),key=lambda kv:kv[1][0])[0];_nar_odds_cache.pop(oldest,None)
    return out

def _attach_nar_live_odds(detail:dict)->dict:
    if not detail:return detail
    odds=_nar_live_odds(str(detail.get("track") or ""),str(detail.get("date") or ""),int(detail.get("raceNumber") or 0))
    if not odds:return detail
    for h in detail.get("horses",[]) or []:
        z=odds.get(int(h.get("horseNumber") or 0))
        if z:h.update({k:v for k,v in z.items() if v is not None and v!=""})
    detail["oddsSource"]="NAR公式"; detail["oddsType"]="単勝実オッズ"; detail["oddsUpdatedAt"]=datetime.now().strftime("%H:%M:%S")
    return detail

def nar_race_detail(race_id: str) -> dict | None:
    m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
    if not m:return None
    iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
    store=NarStore()
    try:
        race=store.conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
        if not race:return None
        entries=store.conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        horses=[]
        for e in entries:
            horses.append({
                "id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),"horseNumber":int(e["horse_no"]),
                "frameNumber":int(e["frame_no"] or 0),"name":e["name"],"age":int(e["age"] or 0),"sex":e["sex"] or "牡",
                "carriedWeight":float(e["carried_weight"] or 0),"jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "jockeyStats":store.stats("jockey",e["jockey"],iso_date),"trainerStats":store.stats("trainer",e["trainer"],iso_date),
                "jockeyProfile":store.role_profile("jockey",e["jockey"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "trainerProfile":store.role_profile("trainer",e["trainer"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "prizeMoneyAtRace":store.prize_before(e["name"],iso_date),"recentRaces":store.recent_races(e["name"],iso_date,5),
            })
        finishers=[]
        for e in entries:
            fin=int(e["finish"] or 0)
            if entries:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"] or 999,x["horseNumber"]))
        need=min(3,len(entries)); ranks={x["finish"] for x in finishers}; finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),"condition":race["condition"] or "不明",
                "weather":race["weather"] or "不明","fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "","scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "startTimeChanged":bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"]!=race["start_time"]),
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,"source":"NAR公式"}
        return detail
    finally:
        try:store.conn.close()
        except Exception:pass




def _nar_attach_recent_batch(detail: dict, limit: int = 5) -> dict:
    """Attach recent NAR runs for all horses with one SQL query, avoiding N+1."""
    if not isinstance(detail,dict) or str(detail.get("circuit") or "")!="地方":
        return detail
    horses=detail.get("horses") or []
    names=[str(h.get("name") or "") for h in horses if h.get("name")]
    cutoff=str(detail.get("date") or "9999-12-31")
    if not names or not DB_PATH.exists():return detail
    conn=_new_conn(DB_PATH)
    try:
        ph=",".join("?" for _ in names)
        sql=f"""
        SELECT e.name,e.date,e.track,e.race_no,e.finish,e.time_seconds,e.corner_positions_json,
               e.carried_weight,e.jockey,e.trainer,
               r.title,r.distance,r.weather,r.condition,r.field_size,r.prize1
        FROM entries e
        JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
        WHERE e.name IN ({ph}) AND e.date<? AND e.finish>0
        ORDER BY e.name,e.date DESC,e.race_no DESC
        """
        rows=conn.execute(sql,[*names,cutoff]).fetchall()
    finally:
        conn.close()
    grouped={n:[] for n in names}
    for row in rows:
        arr=grouped.get(str(row["name"]) or "")
        if arr is None or len(arr)>=limit:continue
        try:cp=json.loads(row["corner_positions_json"] or "[]")
        except Exception:cp=[]
        arr.append({
            "date":row["date"],"track":row["track"],"raceNumber":int(row["race_no"] or 0),
            "raceId":f"nar-{row['date']}-{row['track']}-{int(row['race_no'] or 0):02d}",
            "title":row["title"] or f"{int(row['race_no'] or 0)}R",
            "distance":int(row["distance"] or 0),"condition":row["condition"] or "不明",
            "weather":row["weather"] or "不明","finish":int(row["finish"] or 0),
            "timeSeconds":float(row["time_seconds"] or 0),"cornerPositions":cp,
            "fieldSize":int(row["field_size"] or 0),"racePrize1":int(row["prize1"] or 0),
            "carriedWeight":float(row["carried_weight"] or 0),
            "jockey":row["jockey"] or "","trainer":row["trainer"] or "",
            "source":"NAR公式ローカル履歴",
        })
    for h in horses:
        h["recentRaces"]=grouped.get(str(h.get("name") or ""),[])[:limit]
        h["allPastRuns"]=list(h["recentRaces"])
    return detail


def _horse_key(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", _clean(str(value or "")))


def _central_find_horse(race: dict, horse_name: str) -> tuple[dict | None, dict | None]:
    key = _horse_key(horse_name)
    horse = None
    for h in race.get("horses", []) or []:
        if _horse_key(h.get("name")) == key:
            horse = h
            break
    finisher = None
    result = race.get("result") if isinstance(race.get("result"), dict) else {}
    finishers = result.get("finishers") if isinstance(result.get("finishers"), list) else []
    for f in finishers:
        same_no = horse is not None and int(f.get("horseNumber") or 0) == int(horse.get("horseNumber") or 0)
        same_name = _horse_key(f.get("name")) == key
        if same_no or same_name:
            finisher = f
            break
    return horse, finisher


def _central_run_from_race(race: dict, horse_name: str) -> dict | None:
    horse, fin = _central_find_horse(race, horse_name)
    if horse is None and fin is None:
        return None
    horse = horse or {}
    fin = fin or {}
    finish = int(fin.get("finish") or horse.get("finish") or 0)
    corners = fin.get("cornerPositions") or horse.get("cornerPositions") or []
    if not isinstance(corners, list):
        corners = []
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f_rank=fin.get("last3FRank") or horse.get("last3FRank")
    try:last3f_rank=int(last3f_rank) if last3f_rank not in (None,"") else None
    except (TypeError,ValueError):last3f_rank=None
    last3f_pct=fin.get("last3FPercentile") if fin.get("last3FPercentile") is not None else horse.get("last3FPercentile")
    try:last3f_pct=float(last3f_pct) if last3f_pct is not None else None
    except (TypeError,ValueError):last3f_pct=None
    return {
        "raceId": race.get("id") or "",
        "date": race.get("date") or "",
        "track": race.get("track") or "",
        "raceNumber": int(race.get("raceNumber") or 0),
        "title": race.get("title") or "",
        "distance": int(race.get("distance") or 0),
        "condition": race.get("condition") or "不明",
        "weather": race.get("weather") or "不明",
        "surface": race.get("surface") or "",
        "fieldSize": int(race.get("fieldSize") or len(race.get("horses") or [])),
        "finish": finish,
        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),
        "last3FSeconds": last3f,
        "last3FRank": last3f_rank,
        "last3FPercentile": last3f_pct,
        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],
        "carriedWeight": float(horse.get("carriedWeight") or fin.get("carriedWeight") or 0),
        "racePrize1": int(race.get("racePrize1") or 0),
        "jockey": horse.get("jockey") or fin.get("jockey") or "",
        "trainer": horse.get("trainer") or fin.get("trainer") or "",
        "source": race.get("source") or "中央フィード",
    }


def _central_resolve_race_id(run: dict) -> str:
    if run.get("raceId"):
        return str(run.get("raceId"))
    d = _clean(str(run.get("date") or ""))
    tr = _clean(str(run.get("track") or ""))
    rn = int(run.get("raceNumber") or 0)
    if not d or not tr or rn <= 0 or not CENTRAL_DB_PATH.exists():
        return ""
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM central_races WHERE date=? AND track=? AND race_no=? LIMIT 1",
            (d, tr, rn),
        ).fetchone()
        return str(row["id"]) if row else ""
    finally:
        conn.close()


def _central_recent_from_store(horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
    if not CENTRAL_DB_PATH.exists() or not horse_name:
        return []
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        # Pull newest races first. We stop as soon as this horse has five actual starts.
        rows = conn.execute(
            "SELECT payload FROM central_races WHERE date<? ORDER BY date DESC,track DESC,race_no DESC LIMIT 4000",
            (cutoff,),
        ).fetchall()
        out = []
        seen = set()
        for row in rows:
            try:
                race = json.loads(row["payload"])
            except Exception:
                continue
            run = _central_run_from_race(race, horse_name)
            if not run:
                continue
            key = (run.get("date"), run.get("track"), int(run.get("raceNumber") or 0))
            if key in seen:
                continue
            seen.add(key)
            # A finish can be missing in a future-entry payload. Keep the race only when
            # the historical payload contains an actual result or explicit run result data.
            if int(run.get("finish") or 0) <= 0 and not run.get("cornerPositions") and not float(run.get("timeSeconds") or 0):
                continue
            out.append(run)
            if len(out) >= limit:
                break
        return out
    finally:
        conn.close()


def _merge_central_recent(existing: list[dict], stored: list[dict], cutoff: str, limit: int = 5) -> list[dict]:
    all_runs = []
    seen = set()
    for src in (existing or []) + (stored or []):
        if not isinstance(src, dict):
            continue
        run = dict(src)
        if cutoff and run.get("date") and str(run.get("date")) >= cutoff:
            continue
        rid = _central_resolve_race_id(run)
        if rid:
            run["raceId"] = rid
        key = run.get("raceId") or (str(run.get("date") or "") + "|" + str(run.get("track") or "") + "|" + str(int(run.get("raceNumber") or 0)))
        if key in seen:
            continue
        seen.add(key)
        all_runs.append(run)
    all_runs.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("raceNumber") or 0)), reverse=True)
    return all_runs[:limit]


def _central_month_dates(year: int, month: int, cutoff: str) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    dates = []
    # JRA standard meetings are Sat/Sun and holiday Mondays. Searching these days first
    # avoids hundreds of empty requests while still covering ordinary and holiday meetings.
    for day in range(last, 0, -1):
        d = dt_date(year, month, day)
        if d >= cutoff_date:
            continue
        if d.weekday() in (0, 5, 6):
            dates.append(d.isoformat())
    return dates


def _fetch_central_days_parallel(days: list[str]) -> tuple[list[dict], list[str]]:
    if not days:
        return [], []
    workers = max(2, min(10, int(os.getenv("CENTRAL_HISTORY_WORKERS", "6"))))
    rows: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(days))) as pool:
        future_map = {pool.submit(fetch_central_feed, day, True):day for day in days}
        for fut in as_completed(future_map):
            day = future_map[fut]
            try:
                rows.extend(fut.result() or [])
            except Exception as exc:
                errors.append(f"{day}:{exc}")
    return rows, errors


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
                def fill(h):
                    h=dict(h)
                    try:
                        extra=_jra_profile_runs(h.get("_jraHorseCname") or "",cutoff,5)
                        h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],extra,5)
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
                central_done=(total_now == 0) or (resolved_now >= total_now) or bool(cov_now.get("horsesWithHistory",0))
                with _race_history_lock:
                    _race_history_jobs[race_id]={"status":"done" if central_done else ("error" if errors else "done"),
                        "monthsDone":0,"maxMonths":0,"coverage":cov_now,"error":" | ".join(errors[-5:]),
                        "source":"JRA公式 競走馬情報5走補完"}
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
                if _history_is_enough(cov_now, months_done):
                    break
            fresh_detail = central_race_detail(race_id) or {}
            cov_now = _central_detail_coverage(fresh_detail)
            status = "done" if cov_now.get("horsesWithHistory", 0) > 0 else ("error" if errors else "done")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,
                                               "coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"中央フィード高速並列検索"}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
        finally:
            try:
                store.conn.close()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)



def _parse_netkeiba_win_odds_payload(raw:str)->dict:
    if not raw:return {}
    s=str(raw).strip()
    if not s.startswith("{"):
        m=re.search(r"\((\{.*\})\)\s*;?\s*$",s,re.S)
        if m:s=m.group(1)
    try:body=json.loads(s)
    except Exception:return {}
    data=body.get("data") if isinstance(body,dict) else None
    odds=(data.get("odds") if isinstance(data,dict) else None) or {}
    win=odds.get("1") if isinstance(odds,dict) else None
    if win is None and isinstance(odds,dict):win=odds.get(1)
    if not isinstance(win,dict):return {}
    out={}
    for k,v in win.items():
        try:no=int(str(k))
        except Exception:continue
        odd=None;pop=None
        if isinstance(v,(list,tuple)):
            if len(v)>0:
                candidate=str(v[0]).replace(",","").strip()
                if re.fullmatch(r"\d+(?:\.\d+)?",candidate):
                    try:odd=float(candidate)
                    except Exception:odd=None
            if len(v)>2:
                try:pop=int(float(v[2]))
                except Exception:pop=None
        elif isinstance(v,dict):
            for kk in ("odds","win","tan"):
                if v.get(kk) not in (None,""):
                    try:odd=float(v.get(kk));break
                    except Exception:pass
            for kk in ("popularity","popular","rank","ninki"):
                if v.get(kk) not in (None,""):
                    try:pop=int(float(v.get(kk)));break
                    except Exception:pass
        if odd is not None and odd>0:
            out[no]={"winOdds":odd,"popularity":pop,"oddsSource":"netkeiba実オッズ"}
    return out


def _netkeiba_live_win_odds(detail:dict,force:bool=False)->dict:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return {}
    base="https://race.netkeiba.com/api/api_get_jra_odds.html"
    nonce=f"&t={int(time.time()*1000)}" if force else ""
    common=f"pid=api_get_jra_odds&race_id={urllib.parse.quote(rid)}&type=1&sort=odds&compress=0&output=json"
    urls=[f"{base}?{common}&action=update{nonce}",f"{base}?{common}&action=init{nonce}"]
    for url in urls:
        try:
            raw=_netkeiba_get(url,float(os.getenv("NETKEIBA_ODDS_TIMEOUT_SEC","3.0")),
                              0 if force else int(os.getenv("NETKEIBA_ODDS_CACHE_SEC","8")))
            out=_parse_netkeiba_win_odds_payload(raw)
            if out:return out
        except Exception as exc:
            print("netkeiba odds api failed",rid,exc)
    return {}

def _merge_central_odds(detail:dict, odds:dict)->dict:
    if not odds:return detail
    by={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    for no,z in odds.items():
        h=by.get(int(no))
        if h:
            for k,v in z.items():
                if v not in (None,""):h[k]=v
    detail["oddsSource"]="netkeiba実オッズ";detail["oddsType"]="単勝実オッズ";detail["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    return detail

def _merge_result_fields(detail:dict,result:dict)->dict:
    fins=(result or {}).get("finishers") or []
    if not fins:return detail
    hs=detail.get("horses") if isinstance(detail.get("horses"),list) else []
    by={int(h.get("horseNumber") or 0):h for h in hs if int(h.get("horseNumber") or 0)>0}
    if not hs:
        hs=[];detail["horses"]=hs
    for f in fins:
        no=int(f.get("horseNumber") or 0)
        if not no:continue
        h=by.get(no)
        if h is None:
            h={"horseNumber":no,"frameNumber":int(f.get("frameNumber") or no),"name":str(f.get("name") or ""),"recentRaces":[],"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}}
            hs.append(h);by[no]=h
        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange"):
            if f.get(k) not in (None,""):h[k]=f.get(k)
        if f.get("winOdds"):h["oddsSource"]="netkeiba最終"
    if any(f.get("winOdds") for f in fins):
        detail["oddsSource"]="netkeiba最終";detail["oddsType"]="単勝最終オッズ";detail["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    detail["fieldSize"]=int(detail.get("fieldSize") or len(hs))
    return detail

def _parse_payouts(soup) -> list[dict]:
    """Parse official payout tables robustly, including NAR line-break cells."""
    import unicodedata
    aliases={
        "単勝":"単勝","複勝":"複勝",
        "枠連":"枠連","枠複":"枠連","枠連複":"枠連",
        "馬連":"馬連","馬複":"馬連","馬連複":"馬連",
        "ワイド":"ワイド",
        "馬単":"馬単","馬連単":"馬単",
        "3連複":"3連複","三連複":"3連複","３連複":"3連複",
        "3連単":"3連単","三連単":"3連単","３連単":"3連単",
    }
    label_keys=sorted(aliases,key=len,reverse=True)
    out=[];seen=set()

    def norm(v):
        return re.sub(r"\s+","",unicodedata.normalize("NFKC",str(v or "")))

    def lines(cell):
        copy=BeautifulSoup(str(cell),"html.parser")
        for br in copy.find_all("br"):br.replace_with("\n")
        vals=[]
        for x in copy.get_text("\n").splitlines():
            x=norm(x)
            if x:vals.append(x)
        return vals

    def add(kind,combo,amount):
        kind=aliases.get(kind,kind);combo=norm(combo);amount=norm(amount)
        cm=re.fullmatch(r"\d+(?:[-→・]\d+){0,2}",combo)
        am=re.fullmatch(r"([\d,]+)円?",amount)
        if not cm or not am:return
        value=int(am.group(1).replace(",",""))
        key=(kind,combo,value)
        if key in seen:return
        seen.add(key)
        out.append({"type":kind,"combination":combo,"amount":value})

    for table in soup.find_all("table"):
        current=""
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"],recursive=False)
            if not cells:continue
            cell_lines=[lines(c) for c in cells]
            flat=[x for group in cell_lines for x in group]
            label_i=None;label_raw=""
            for i,group in enumerate(cell_lines):
                for v in group:
                    hit=next((k for k in label_keys if norm(v)==norm(k)),None)
                    if hit:
                        label_i=i;label_raw=hit;break
                if label_i is not None:break
            if label_i is not None:
                current=aliases[label_raw]
                payload=[x for group in cell_lines[label_i+1:] for x in group]
            elif current:
                payload=flat
            else:
                continue

            combos=[x for x in payload if re.fullmatch(r"\d+(?:[-→・]\d+){0,2}",norm(x))]
            amounts=[x for x in payload if re.fullmatch(r"[\d,]+円",norm(x))]
            if combos and amounts:
                for combo,amount in zip(combos,amounts):
                    add(current,combo,amount)

    if not out:
        raw=unicodedata.normalize("NFKC",soup.get_text("\n"))
        raw=re.sub(r"[ \t]+","",raw)
        labels="|".join(re.escape(k) for k in label_keys)
        chunks=list(re.finditer(rf"(?m)^({labels})\s*$",raw))
        for idx,m in enumerate(chunks):
            kind=aliases.get(norm(m.group(1)),norm(m.group(1)))
            seg=raw[m.end():chunks[idx+1].start() if idx+1<len(chunks) else m.end()+500]
            combos=re.findall(r"(?m)^(?:\s*)(\d+(?:[-→・]\d+){0,2})(?:\s*)$",seg)
            amounts=re.findall(r"([\d,]+)\s*円",seg)
            for combo,amount in zip(combos,amounts):
                add(kind,combo,amount+"円")
    return out


def _fetch_nar_payouts_only(detail: dict) -> tuple[list[dict],str]:
    code=NAR_BABA_CODES.get(detail.get("track"))
    if not code:return [],"競馬場コード未取得"
    query=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":str(detail.get("date") or "").replace("-","/"),
        "k_raceNo":int(detail.get("raceNumber") or 0),
    })
    urls=[
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
    ]
    last=""
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja,en-US;q=0.8",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_PAYOUT_TIMEOUT_SEC","2.0"))) as response:
                html=_jra_decode(response.read())
            payouts=_parse_payouts(BeautifulSoup(html,"html.parser"))
            if payouts:return payouts,url
            last="払戻表は取得したが解析結果0件"
        except Exception as exc:
            last=str(exc)
    return [],last or "払い戻し未取得"


def _attach_nar_payouts(detail: dict) -> dict:
    result=detail.get("result")
    if not isinstance(result,dict):
        result={}
        detail["result"]=result
    if result.get("payouts"):return detail
    payouts,source=_fetch_nar_payouts_only(detail)
    if payouts:
        result["payouts"]=payouts
        result["status"]="確定"
        result["payoutSource"]="NAR公式"
        result["payoutUrl"]=source
        result.pop("payoutError",None)
    else:
        result["payoutError"]="払い戻し未取得"
        result["payoutDebug"]=source[:240]
    return detail


def _netkeiba_current_result(detail:dict)->dict|None:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return None
    try:html=_netkeiba_get(f"https://race.netkeiba.com/race/result.html?race_id={rid}",float(os.getenv("NETKEIBA_RESULT_TIMEOUT_SEC","3.0")),20)
    except Exception as exc:
        print("netkeiba result failed",rid,exc);return None
    soup=BeautifulSoup(html,"html.parser"); table=None; headers=[]
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr")[:4]:
            vals=[re.sub(r"\s+","",_clean(c.get_text(" ",strip=True))) for c in tr.find_all(["th","td"])]
            if any("着順" in v for v in vals) and any("馬番" in v for v in vals) and any("馬名" in v for v in vals):
                table=tb;headers=vals;break
        if table:break
    if table is None:return None
    def hidx(*keys):
        for i,v in enumerate(headers):
            for k in keys:
                if k in v:return i
        return -1
    i_fin=hidx("着順");i_frame=hidx("枠");i_no=hidx("馬番");i_name=hidx("馬名");i_time=hidx("タイム");i_corner=hidx("コーナー通過順");i_pop=hidx("人気");i_odds=hidx("単勝オッズ","単勝");i_bw=hidx("馬体重")
    finishers=[]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if not tds:continue
        vals=[_clean(td.get_text(" ",strip=True)) for td in tds]
        def val(i):return vals[i] if 0<=i<len(vals) else ""
        fm=re.search(r"\d+",val(i_fin)) if i_fin>=0 else None
        fin=int(fm.group()) if fm else 0; no=0; frame=0
        mn=re.search(r"\d+",val(i_no)) if i_no>=0 else None
        mf=re.search(r"\d+",val(i_frame)) if i_frame>=0 else None
        if mn:no=int(mn.group())
        if mf:frame=int(mf.group())
        if not no:
            um=tr.find("td",class_=re.compile(r"Umaban",re.I))
            mm=re.search(r"\d+",_clean(um.get_text(" ",strip=True))) if um else None
            if mm:no=int(mm.group())
        name=val(i_name)
        if not name:
            na=tr.select_one(".Horse_Name a,.HorseInfo a,.Horse_Name")
            name=_clean(na.get_text(" ",strip=True)) if na else ""
        tm=_jra_parse_time_seconds(val(i_time)) if i_time>=0 else 0.0
        corners=[]
        cs=val(i_corner)
        cm=re.search(r"\d{1,2}(?:-\d{1,2})+",cs)
        if cm:corners=[int(x) for x in cm.group().split("-")]
        pop=None;odd=None;bw=None;chg=None
        mp=re.search(r"\d+",val(i_pop)) if i_pop>=0 else None
        if mp:
            try:pop=int(mp.group())
            except Exception:pass
        mo=re.search(r"\d+(?:\.\d+)?",val(i_odds)) if i_odds>=0 else None
        if mo:
            try:odd=float(mo.group())
            except Exception:pass
        mb=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",val(i_bw)) if i_bw>=0 else None
        if mb:
            try:bw=int(mb.group(1));chg=int(mb.group(2)) if mb.group(2) is not None else None
            except Exception:pass
        if no and name:finishers.append({"finish":fin,"finishLabel":str(fin)+"着" if fin else val(i_fin),"horseNumber":no,"frameNumber":frame,"name":name,"timeSeconds":tm,"cornerPositions":corners,"winOdds":odd,"popularity":pop,"bodyWeight":bw,"bodyWeightChange":chg})
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    if len(finishers)<3:return None
    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",_clean(soup.get_text(" ",strip=True))) else "速報"
    return {"status":status,"finishers":finishers,"source":"netkeiba結果","payouts":payouts}


def _jra_result_cname_from_card(cname:str)->str:
    if not cname:return ""
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20)
    except Exception as exc:
        print("JRA result link fetch failed",exc);return ""
    vals=[_jra_norm_cname(x) for x in JRA_RESULT_CNAME_RE.findall(html)]
    return vals[0] if vals else ""

def _jra_any_track(cname:str)->str:
    m=re.search(r"pw01(?:d|s)de(?:01|10)(\d{2})",cname or "",re.I)
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""

def _jra_any_race_no(cname:str)->int:
    m=re.search(r"pw01(?:d|s)de(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "",re.I)
    return int(m.group(1)) if m else 0

def _jra_parse_result(result_cname:str,base:dict|None=None)->dict|None:
    if not result_cname:return None
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessS.html",result_cname,20)
    except Exception as exc:
        print("JRA official result fetch failed",result_cname,exc);return None
    soup=BeautifulSoup(html,"html.parser");full=_jra_text(soup)
    date=_jra_date_from_cname(result_cname) or str((base or {}).get("date") or "")
    track=_jra_any_track(result_cname) or str((base or {}).get("track") or "")
    race_no=_jra_any_race_no(result_cname) or int((base or {}).get("raceNumber") or 0)
    sm=re.search(r"発走時刻\s*[：:]?\s*(\d{1,2})時\s*(\d{2})分",full)
    start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else str((base or {}).get("startTime") or "")
    dm=re.search(r"コース\s*[：:]?\s*([\d,]+)\s*メートル\s*[（(]([^）)]+)[）)]",full)
    distance=int(dm.group(1).replace(",","")) if dm else int((base or {}).get("distance") or 0)
    desc=dm.group(2) if dm else str((base or {}).get("surface") or "")
    surface="障害" if "障" in desc else ("芝" if "芝" in desc else ("ダート" if "ダ" in desc else str((base or {}).get("surface") or "")))
    weather="不明";wm=re.search(r"天候\s*[：:]?\s*(晴|曇|雨|小雨|雪|小雪)",full)
    if wm:weather=wm.group(1)
    conds=[]
    for typ in ("芝","ダート"):
        cm=re.search(typ+r"\s*[：:]?\s*(良|稍重|重|不良)",full)
        if cm:conds.append((typ,cm.group(1)))
    condition="不明"
    if surface=="芝":condition=next((c for t,c in conds if t=="芝"),condition)
    elif surface=="ダート":condition=next((c for t,c in conds if t=="ダート"),condition)
    elif conds:condition=conds[-1][1]
    title=""
    for node in soup.find_all(["h2","h3"]):
        tx=_jra_text(node)
        if tx and len(tx)<100 and not JRA_BAD_TITLE_RE.search(tx) and "レース結果" not in tx and not re.match(r"^\d+レース$",tx):title=tx;break
    if not title:title=str((base or {}).get("title") or f"{race_no}R")
    table=None;headers=[]
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr")[:5]:
            vals=[re.sub(r"\s+","",_jra_text(c)) for c in tr.find_all(["th","td"])]
            if any("着順" in v for v in vals) and any("馬番" in v for v in vals) and any("馬名" in v for v in vals):table=tb;headers=vals;break
        if table:break
    if table is None:return None
    def hidx(*keys):
        for i,v in enumerate(headers):
            for k in keys:
                if k in v:return i
        return -1
    ix={"fin":hidx("着順"),"frame":hidx("枠"),"no":hidx("馬番"),"name":hidx("馬名"),"sexage":hidx("性齢"),"cw":hidx("負担重量","斤量"),"jockey":hidx("騎手名","騎手"),"time":hidx("タイム"),"last3f":hidx("推定上り","上り"),"corner":hidx("コーナー通過順位","コーナー通過順"),"bw":hidx("馬体重"),"trainer":hidx("調教師名","調教師"),"pop":hidx("単勝人気","人気")}
    finishers=[]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if not tds:continue
        vals=[_jra_text(td) for td in tds]
        def val(k):
            i=ix[k];return vals[i] if 0<=i<len(vals) else ""
        fm=re.search(r"\d+",val("fin"));nm=re.search(r"\d+",val("no"))
        if not nm:continue
        fin=int(fm.group()) if fm else 0;no=int(nm.group());mf=re.search(r"\d+",val("frame"));frame=int(mf.group()) if mf else 0
        name=_clean(val("name"));sxage=val("sexage");sx="";age=0;smx=re.search(r"(牡|牝|せん)(\d+)",sxage)
        if smx:sx=smx.group(1);age=int(smx.group(2))
        mcw=re.search(r"\d+(?:\.\d+)?",val("cw"));cw=float(mcw.group()) if mcw else 0.0
        tm=_jra_parse_time_seconds(val("time"));m3=re.search(r"\d+(?:\.\d+)?",val("last3f"));last3f=float(m3.group()) if m3 else None;corners=[];cm=re.search(r"\d{1,2}(?:-\d{1,2})+",val("corner"))
        if cm:corners=[int(x) for x in cm.group().split("-")]
        elif val("corner"):corners=[int(x) for x in re.findall(r"\d{1,2}",val("corner"))]
        bw=None;chg=None;mb=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",val("bw"))
        if mb:bw=int(mb.group(1));chg=int(mb.group(2)) if mb.group(2) is not None else None
        mp=re.search(r"\d+",val("pop"));pop=int(mp.group()) if mp else None
        finishers.append({"finish":fin,"finishLabel":str(fin)+"着" if fin else val("fin"),"horseNumber":no,"frameNumber":frame,"name":name,"sex":sx,"age":age,"carriedWeight":cw,"jockey":_clean(val("jockey")),"trainer":_clean(val("trainer")),"timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw,"bodyWeightChange":chg,"popularity":pop})
    sectionals=sorted({float(x.get("last3FSeconds")) for x in finishers if x.get("last3FSeconds") not in (None,"") and float(x.get("last3FSeconds"))>0})
    for x in finishers:
        try:s=float(x.get("last3FSeconds")) if x.get("last3FSeconds") not in (None,"") else 0.0
        except (TypeError,ValueError):s=0.0
        if s>0 and sectionals:
            rk=sectionals.index(s)+1
            x["last3FRank"]=rk
            x["last3FPercentile"]=0.5 if len(sectionals)==1 else 1.0-(rk-1)/(len(sectionals)-1)
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    if not finishers:return None
    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",full) else "速報"
    prize1=0
    pm=re.search(r"1着\s*([\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except (TypeError,ValueError):prize1=0
    return {"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(finishers),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"result":{"status":status,"finishers":finishers,"source":"JRA公式","payouts":payouts},"resultCname":result_cname,"source":"JRA公式結果"}
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
    detail=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:detail=json.loads(row["payload"])
                except Exception as exc:print("central payload decode failed",race_id,exc)
        finally:conn.close()
    if detail is None:
        mm=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",str(race_id or ""))
        if mm:
            detail=_jra_program_lookup(mm.group(1),mm.group(2),int(mm.group(3)))
            if detail:
                detail["id"]=race_id
                try:st=CentralStore();st.upsert([detail]);st.conn.close()
                except Exception as exc:print("central fallback cache save failed",exc)
    if detail is None:return None
    date=str(detail.get("date") or "");track=str(detail.get("track") or "");race_no=int(detail.get("raceNumber") or 0)
    program=_jra_program_lookup(date,track,race_no)
    if program:
        for k in ("title","distance","surface","startTime","scheduledStartTime","meetingNumber","meetingDay","netkeibaRaceId"):
            v=program.get(k)
            if v not in (None,"",0):detail[k]=v
    if not detail.get("netkeibaRaceId"):detail["netkeibaRaceId"]=_netkeiba_program_race_id(date,track,race_no)
    cname=str(detail.get("jraCname") or "")
    should_result=_race_should_have_result(detail)
    if not cname and (should_result or not (detail.get("horses") or []) or int(detail.get("distance") or 0)<=0):
        cname=_jra_find_cname(date,track,race_no)
        if cname:detail["jraCname"]=cname
    # Finished race: fetch JRA official result first. This also supplies exact weather/going.
    if should_result and cname:
        try:
            rc=str(detail.get("resultCname") or "") or _jra_result_cname_from_card(cname)
            if rc:
                official=_jra_parse_result(rc,detail)
                if official:detail=_merge_official_result(detail,official)
        except Exception as exc:print("JRA official result hydrate failed",race_id,exc)
    # Official JRA card is primary for the pre-race card and live body data.
    malformed=(not (detail.get("horses") or []) or bool(JRA_BAD_TITLE_RE.search(str(detail.get("title") or ""))) or int(detail.get("distance") or 0)<=0)
    if cname:
        try:
            live=_jra_parse_race(cname,supplement_profiles=False)
            if live:
                if malformed:
                    # Keep any official result already obtained, but replace the card with the official entry data.
                    saved_result=detail.get("result");saved_rc=detail.get("resultCname")
                    detail=live
                    if saved_result:detail["result"]=saved_result
                    if saved_rc:detail["resultCname"]=saved_rc
                else:
                    for k in ("title","distance","surface","condition","weather","fieldSize","startTime","scheduledStartTime"):
                        v=live.get(k)
                        if v not in (None,"",0,"不明"):detail[k]=v
                    by_no={int(h.get("horseNumber") or 0):h for h in live.get("horses",[]) or []}
                    for h in detail.get("horses",[]) or []:
                        z=by_no.get(int(h.get("horseNumber") or 0))
                        if z:
                            for k in ("bodyWeight","bodyWeightChange","sex","age","carriedWeight","jockey","trainer"):
                                if z.get(k) not in (None,"",0,[]):h[k]=z.get(k)
                            if z.get("recentRaces"):
                                h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)
        except Exception as exc:print("JRA official card hydrate failed",race_id,exc)
    # If the official card is unavailable (e.g. publication ended), fill missing card rows from netkeiba.
    if not (detail.get("horses") or []):
        try:
            nr=_netkeiba_detail_rows(detail)
            if nr:
                for h in nr:
                    h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
                detail["horses"]=nr;detail["fieldSize"]=len(nr);detail.setdefault("dataSources",[])
                if "netkeiba" not in detail["dataSources"]:detail["dataSources"].append("netkeiba")
        except Exception as exc:print("central card fallback failed",race_id,exc)
    # Before official results exist, fill only missing weather/going from a secondary public race page.
    if detail.get("condition") in (None,"","不明") or detail.get("weather") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(detail)
            for k in ("title","distance","condition","weather","startTime"):
                if detail.get(k) in (None,"",0,"不明") and meta.get(k) not in (None,"",0,"不明"):detail[k]=meta[k]
        except Exception as exc:print("central race meta fallback failed",race_id,exc)
    # Result fallback only if JRA official result link was not available yet.
    if should_result and not (detail.get("result") and (detail.get("result") or {}).get("finishers")):
        try:
            rr=_netkeiba_current_result(detail)
            if rr:
                for f in rr.get("finishers",[]) or []:f.pop("winOdds",None)
                detail["result"]=rr
                # Populate result/body fields without odds.
                hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs}
                for f in rr.get("finishers",[]) or []:
                    h=by_no.get(int(f.get("horseNumber") or 0))
                    if h:
                        for k in ("bodyWeight","bodyWeightChange"):
                            if f.get(k) not in (None,""):h[k]=f.get(k)
        except Exception as exc:print("central result fallback failed",race_id,exc)
    detail.pop("oddsSource",None);detail.pop("oddsType",None);detail.pop("oddsUpdatedAt",None)
    for h in detail.get("horses",[]) or []:
        h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
    if detail.get("horses") or detail.get("result"):
        try:st=CentralStore();st.upsert([detail]);st.conn.close()
        except Exception as exc:print("central hydrated cache save failed",exc)
    cutoff=str(detail.get("date") or "9999-12-31")
    for h in detail.get("horses",[]) or []:
        try:
            stored=_central_recent_from_store(str(h.get("name") or ""),cutoff,5)
            h["recentRaces"]=_merge_central_recent(h.get("recentRaces") or [],stored,cutoff,5)
        except Exception as exc:
            print("central horse history merge failed",race_id,h.get("name"),exc)
            h["recentRaces"]=[x for x in (h.get("recentRaces") or []) if isinstance(x,dict)][:5]
    return detail

# --- v68 compact rows + fast JRA summaries; official data stays authoritative ---
_smart_cache_lock=threading.Lock(); _smart_cache:dict[str,tuple[float,dict]]={}
_enrich_jobs_lock=threading.Lock(); _enrich_jobs:dict[str,dict]={}
_enrich_data_lock=threading.Lock(); _enrich_data:dict[str,dict]={}

def _safe_float(v):
    try:
        if v is None or v=="": return None
        if isinstance(v,str):
            m=re.search(r"-?\d+(?:\.\d+)?",v.replace(",","").strip())
            if not m:return None
            v=m.group(0)
        return float(v)
    except Exception:return None

def _safe_int(v):
    x=_safe_float(v); return int(x) if x is not None else None

def _smart_normalize_row(x:dict)->dict|None:
    if not isinstance(x,dict):return None
    no=_safe_int(_pick(x,"horseNumber","horse_no","uno","number","馬番")); name=str(_pick(x,"name","hname","horseName","馬名") or "").strip()
    if not no and not name:return None
    smart={"ten1f":_pick(x,"ten1f","ten1f_best","h1_ten1f","テン1F"),"ten":_pick(x,"ten","ten_pat","ten_has","テン"),"agari":_pick(x,"agari","agari3f","furlong3","agari_pat","agari_has","上がり"),"estimatedPopularity":_pick(x,"estimatedPopularity","est_pop","推人","推定人気")}
    out={"horseNumber":no,"name":name,"smartRc":smart}
    rr=_pick(x,"recentRaces","recent_races")
    if isinstance(rr,list):out["recentRaces"]=[z for z in rr if isinstance(z,dict)][:5]
    return out

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

def _merge_enrichment(detail:dict,data:dict)->dict:
    hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs if h.get("horseNumber")};by_name={str(h.get("name") or "").strip():h for h in hs if h.get("name")};sources=[]
    for row in data.get("smartRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        if "SmartRc" not in sources:sources.append("SmartRc")
        if row.get("smartRc"):h["smartRc"]={**(h.get("smartRc") or {}),**row.get("smartRc")}
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        for k in ("owner","producer","birthday"):
            if h.get(k) in (None,"") and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("recentRaces"):h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
    for row in data.get("netkeibaRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        sources.append("netkeiba") if "netkeiba" not in sources else None
        for k in ("sex","age","carriedWeight","jockey","trainer","bodyWeight","bodyWeightChange","owner","producer"):
            if (h.get(k) in (None,"",0)) and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        if row.get("_netkeibaHorseId"):h["_netkeibaHorseId"]=row.get("_netkeibaHorseId")
        if row.get("recentRaces"):
            h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
    for b in data.get("extra") or []:
        src=str(b.get("source") or "補助")
        for row in b.get("rows") or []:
            h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
            if h:
                extra=_strip_excluded(row.get("extra") or {})
                h.setdefault("extraSources",{})[src]=extra
                for key in ("pedigree","jockeyStats","trainerStats","jumpJockeyStats","jumpTrainerStats","jumpStats","isTransfer","transferFrom","ten1f","agari3f","pedigreeScore","distanceSuitabilityScore","surfaceSuitabilityScore","drawScore","bodyWeightScore","opponentLevelScore","lapScore","conditionChangeScore","jockeyScore","trainerScore","jumpJockeyScore","jumpTrainerScore"):
                    if extra.get(key) is not None:h[key]=extra[key]
                if isinstance(extra.get("allPastRuns"),list):h["allPastRuns"]=extra["allPastRuns"]
        if src not in sources:sources.append(src)
    base=list(detail.get("dataSources") or []);official="JRA公式" if detail.get("circuit")=="中央" else "NAR公式"
    for s in [official]+sources:
        if s not in base:base.append(s)
    detail["dataSources"]=base;return detail

def _enrichment_status(race_id:str)->dict:
    with _enrich_jobs_lock:
        st=_enrich_jobs.get(race_id);return dict(st) if st else {"status":"idle","sources":[],"error":""}

def _start_enrichment(race_id:str,detail:dict,force:bool=False,horse_no:int|None=None)->dict:
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

def _apply_enrichment(race_id:str,detail:dict)->dict:
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



# --- v123 live weather / going -----------------------------------------
_environment_lock=threading.Lock()
_environment_running:set[str]=set()
_environment_state:dict[str,dict]={}
_environment_http_lock=threading.Lock()
_environment_http_cache:dict[str,tuple[float,dict]]={}

def _env_clean_weather(v:str)->str:
    s=_clean(v)
    for x in ("小雨","小雪","晴","曇","雨","雪"):
        if x in s:return x
    return "不明"

def _env_clean_condition(v:str)->str:
    s=_clean(v)
    for x in ("不良","稍重","重","良"):
        if x in s:return x
    return "不明"

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

def _parse_jra_environment_html(html:str, surface:str="")->dict:
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

def _environment_http_get(url:str, ttl:int=30)->str:
    now=time.time()
    with _environment_http_lock:
        hit=_environment_http_cache.get(url)
        if hit and now-hit[0]<ttl:return str(hit[1].get("html") or "")
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
        "Accept-Language":"ja-JP,ja;q=0.9",
    })
    with urllib.request.urlopen(req,timeout=float(os.getenv("RACE_ENV_TIMEOUT_SEC","2.8"))) as res:
        html=_jra_decode(res.read())
    with _environment_http_lock:
        _environment_http_cache[url]=(now,{"html":html})
        if len(_environment_http_cache)>80:
            oldest=min(_environment_http_cache.items(),key=lambda kv:kv[1][0])[0]
            _environment_http_cache.pop(oldest,None)
    return html

def _nar_fetch_environment(track:str, iso_date:str, race_no:int)->dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code or not race_no:return {}
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no)})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
    ]
    out={}
    for url in urls:
        try:parsed=_parse_nar_environment_html(_environment_http_get(url,25 if iso_date==_today_iso() else 86400))
        except Exception as exc:
            print("NAR environment fetch failed",track,iso_date,race_no,exc);continue
        for k in ("weather","condition"):
            if parsed.get(k) not in (None,"","不明"):out[k]=parsed[k]
        if parsed.get("scratchMap"):out["scratchMap"]=parsed["scratchMap"]
        if out.get("weather") and out.get("condition") and "scratchMap" in out:break
    if out:
        out.update({"source":"NAR公式","updatedAtEpoch":int(time.time()),"raceNo":int(race_no)})
    return out

def _jra_fetch_environment(row:dict)->dict:
    date=str(row.get("date") or "")
    track=str(row.get("track") or "")
    race_no=int(row.get("raceNumber") or 0)
    surface=str(row.get("surface") or "")
    cname=str(row.get("jraCname") or "")
    if not cname:
        try:cname=_jra_find_cname(date,track,race_no)
        except Exception:cname=""
    out={}
    if cname:
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20 if date==_today_iso() else 86400)
            out=_parse_jra_environment_html(html,surface)
        except Exception as exc:
            print("JRA environment official failed",date,track,race_no,exc)
    # Secondary source only fills a field the official page did not provide.
    if out.get("weather") in (None,"","不明") or out.get("condition") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(row)
            if out.get("weather") in (None,"","不明") and meta.get("weather") not in (None,"","不明"):
                out["weather"]=_env_clean_weather(meta.get("weather"))
            if out.get("condition") in (None,"","不明") and meta.get("condition") not in (None,"","不明"):
                out["condition"]=_env_clean_condition(meta.get("condition"))
        except Exception as exc:
            print("JRA environment secondary failed",date,track,race_no,exc)
    if out.get("weather") not in (None,"","不明") or out.get("condition") not in (None,"","不明"):
        out.update({"source":"JRA公式優先","updatedAtEpoch":int(time.time())})
    return out

def _race_minutes_server(row:dict)->int:
    m=re.match(r"^(\d{1,2}):(\d{2})",str(row.get("startTime") or row.get("scheduledStartTime") or ""))
    return int(m.group(1))*60+int(m.group(2)) if m else 9999

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


def _safe_body_weight_value(value):
    if value in (None,""):return None
    try:
        m=re.search(r"(?<!\d)(\d{3})(?!\d)",str(value))
        x=int(m.group(1)) if m else int(round(float(value)))
    except Exception:return None
    return x if 250<=x<=800 else None


def _safe_carried_weight_value(value, body_weight=None):
    if value in (None,""):return None
    try:x=float(re.sub(r"[^0-9.+-]","",str(value)))
    except Exception:return None
    # Strict mode: 斤量 is already a kg value. Do not auto-divide 3-digit values,
    # because a horse body weight such as 500 can otherwise become a false 50kg.
    if 35<=x<=80:return round(x,1)
    return None


def _sanitize_horse_measurements(h:dict)->dict:
    if not isinstance(h,dict):return h
    z=dict(h)
    bw=_safe_body_weight_value(z.get("bodyWeight") or z.get("horseWeight") or z.get("currentBodyWeight"))
    z["bodyWeight"]=bw
    ch=z.get("bodyWeightChange")
    try:ch=int(float(ch)) if ch not in (None,"") else None
    except Exception:ch=None
    z["bodyWeightChange"]=ch if ch is not None and abs(ch)<=99 else None
    z["carriedWeight"]=_safe_carried_weight_value(z.get("carriedWeight"),bw)
    runs=[]
    for rr in list(z.get("allPastRuns") or z.get("recentRaces") or []):
        if not isinstance(rr,dict):continue
        q=dict(rr);rbw=_safe_body_weight_value(q.get("bodyWeight"));q["bodyWeight"]=rbw
        q["carriedWeight"]=_safe_carried_weight_value(q.get("carriedWeight"),rbw)
        runs.append(q)
    if z.get("allPastRuns") is not None:z["allPastRuns"]=runs
    z["recentRaces"]=runs[:5]
    return z


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

_full_history_lock=threading.Lock()
_full_history_running:set[str]=set()

def _schedule_full_history_harvest(detail: dict) -> None:
    """Persist every career run exposed by the currently available official source without blocking the race screen."""
    if not bool(int(os.getenv("RACEDB_FULL_HISTORY","1"))) or not isinstance(detail,dict):return
    # Historical/final cards also need pre-race career data for backtests.
    # Source functions receive the race-date cutoff, so later races are excluded.
    if not detail.get("date"):return
    race_id=str(detail.get("id") or "");horses=[h for h in (detail.get("horses") or []) if isinstance(h,dict) and h.get("name")]
    if not race_id or not horses:return
    with _full_history_lock:
        if race_id in _full_history_running:return
        _full_history_running.add(race_id)
    def worker():
        ttl=max(1800,int(os.getenv("RACEDB_FULL_HISTORY_TTL_SEC","21600")));cutoff=str(detail.get("date") or _today_iso());circuit=str(detail.get("circuit") or "")
        try:
            if circuit=="地方":
                store=NarStore()
                try:
                    for h in horses:
                        key="fullhist:nar:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                        if last and int(time.time())-last<ttl:continue
                        try:
                            runs=store.recent_races(str(h.get("name") or ""),cutoff,100000)
                            n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                        except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                finally:
                    try:store.conn.close()
                    except Exception:pass
            else:
                def one(h):
                    key="fullhist:jra:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                    if last and int(time.time())-last<ttl:return
                    cname=str(h.get("_jraHorseCname") or "")
                    if not cname:
                        RACEDB.mark_source(key,"unavailable","JRA horse id unavailable");return
                    try:
                        runs=_jra_profile_runs(cname,cutoff,10000)
                        n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                    except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                workers=max(1,min(4,int(os.getenv("RACEDB_FULL_HISTORY_WORKERS","3"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:list(pool.map(one,horses))
            latest,_=PREPARED_STORE.get(race_id)
            if latest:
                latest=_precompute_detail_metrics(_attach_evaluation_context(_attach_stored_career(latest)))
                latest.setdefault("historySearch",{})["status"]="complete-local-history"
                pm=latest.setdefault("preparedMeta",{})
                pm.pop("diagnosisVersion",None)
                pm["diagnosisReady"]=False
                PREPARED_STORE.put(latest,force=True)
                RACEDB.upsert_race(latest)
        finally:
            with _full_history_lock:_full_history_running.discard(race_id)
    threading.Thread(target=worker,daemon=True).start()

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


def _snapshot_final(detail: dict) -> bool:
    result=detail.get("result") or {}
    return result.get("status")=="確定" and bool(result.get("finishers"))


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
            if detail.get("analysisMode")!="新馬" and _race_history_status(race_id) is None and resolved<total:_start_central_history_search(race_id,detail.get("date") or _today_iso())
    except Exception as exc:
        print("prepared history schedule failed",race_id,exc)


def _schedule_detail_background_jobs(race_id: str, detail: dict) -> None:
    threading.Thread(target=_ensure_detail_background_jobs,args=(race_id,detail),daemon=True).start()


_racedb_refresh_lock=threading.Lock()
_racedb_refresh_running:set[str]=set()

def _fast_local_race_detail(race_id:str)->dict|None:
    """First paint from local DB only. Never wait on web/history/profile lookups."""
    now=int(time.time())
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m or not DB_PATH.exists():return None
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        conn=_new_conn(DB_PATH)
        try:
            race=conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
            if not race:return None
            entries=conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        finally:conn.close()
        if not entries:return None
        horses=[];finishers=[]
        for e in entries:
            horses.append({"id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),
                "horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],
                "age":int(e["age"] or 0),"sex":e["sex"] or "牡","carriedWeight":float(e["carried_weight"] or 0),
                "jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "recentRaces":[],
                "jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{},
                "collectionState":{"status":"basic","history":"loading","pastRunCount":0}})
            fin=int(e["finish"] or 0)
            if fin>0:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),
                                  "name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"],x["horseNumber"]))
        need=min(3,len(entries));ranks={x["finish"] for x in finishers}
        finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),
                "condition":race["condition"] or "不明","weather":race["weather"] or "不明",
                "fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "",
                "scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,
                "source":"NAR公式・高速Snapshot"}
    else:
        if not CENTRAL_DB_PATH.exists():return None
        conn=_new_conn(CENTRAL_DB_PATH)
        try:row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
        finally:conn.close()
        if not row:return None
        try:detail=json.loads(row["payload"])
        except Exception:return None
        if not isinstance(detail,dict) or not (detail.get("horses") or []):return None
        detail=dict(detail);detail["id"]=race_id
        for h in detail.get("horses",[]) or []:
            if not isinstance(h,dict):continue
            runs=list(h.get("recentRaces") or h.get("allPastRuns") or [])[:5]
            h["recentRaces"]=runs;h.pop("allPastRuns",None)
            h.setdefault("jockeyStats",{});h.setdefault("trainerStats",{})
            h.setdefault("jockeyProfile",{});h.setdefault("trainerProfile",{})
            h["collectionState"]={"status":"complete" if runs else "basic",
                                  "history":"available" if runs else "loading","pastRunCount":len(runs)}
        detail["source"]=str(detail.get("source") or "JRA")+"・高速Snapshot"
    try:
        latest=RACEDB.odds_latest(race_id);by={int(x.get("horseNumber") or 0):x for x in latest}
        for h in detail.get("horses",[]) or []:
            z=by.get(int(h.get("horseNumber") or 0))
            if z:
                if z.get("winOdds") is not None:h["winOdds"]=z["winOdds"]
                if z.get("popularity") is not None:h["popularity"]=z["popularity"]
    except Exception:pass
    title=str(detail.get("title") or "");surface=str(detail.get("surface") or "")
    detail["analysisMode"]="障害" if (surface=="障害" or "障害" in title or "ジャンプ" in title) else ("新馬" if re.search(r"(?:新馬|メイクデビュー)",title) else "平地")
    try:
        saved_analysis=RACEDB.get_analysis(race_id)
        if saved_analysis:detail["analysis"]=saved_analysis
    except Exception:pass
    detail["preparedMeta"]={"prepared":True,"fastPartial":True,"preparedAtEpoch":now,"build":"v93-fast"}
    return detail


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
    """Parse the NAR official card including layouts where 馬体重 and 増減 are separate cells."""
    if not html:return []
    soup=BeautifulSoup(html,"html.parser")
    known={_clean(h.get("name")):int(h.get("horseNumber") or 0)
           for h in detail.get("horses",[]) or []
           if h.get("name") and int(h.get("horseNumber") or 0)>0}
    out_by_no={}

    def horse_no_from_row(tr, vals, rowtxt):
        for name,hno in known.items():
            if name and name in rowtxt:return hno
        # Prefer the explicit 馬番 area near the start of the row.
        nums=[]
        for c in vals[:8]:
            m=re.fullmatch(r"\D*(\d{1,2})\D*",c)
            if m:
                v=int(m.group(1))
                if 1<=v<=18:nums.append(v)
        return nums[-1] if nums else 0

    def parse_weight_cell(txt):
        m=re.search(r"(?<!\d)(\d{3})(?:\s*(?:kg)?)?(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?(?!\d)",txt,re.I)
        if not m:return None,None
        w=int(m.group(1))
        if not (250<=w<=800):return None,None
        c=int(m.group(2)) if m.group(2) is not None else None
        return w,c

    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue

        # Try the header-driven layout first. NAR often publishes 馬体重 and 変更
        # in separate columns, so the old "(+/-)"-only parser missed every horse.
        header_vals=[];header_idx=-1
        for ri,tr in enumerate(rows[:8]):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
            compact=[re.sub(r"\s+","",x) for x in vals]
            if any("馬体重" in x for x in compact):
                header_vals=compact;header_idx=ri;break

        ibw=-1;ichg=-1;icw=-1
        if header_vals:
            for i,x in enumerate(header_vals):
                if ibw<0 and "馬体重" in x:ibw=i
                if ichg<0 and ("変更" in x or "増減" in x):ichg=i
                if icw<0 and ("負担重量" in x or "斤量" in x or x=="重量"):icw=i

        for tr in rows[(header_idx+1 if header_idx>=0 else 0):]:
            cells=tr.find_all(["th","td"],recursive=False)
            vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
            rowtxt=_clean(tr.get_text(" ",strip=True))
            if not vals or not rowtxt:continue
            no=horse_no_from_row(tr,vals,rowtxt)
            if not no:continue

            weight=None;change=None;carried=None

            # Current carried weight is independent from body weight. Some NAR layouts
            # publish it as 負担重量 / 斤量, so fill a missing DB value from the card.
            if icw>=0 and icw<len(vals):
                cm=re.search(r"(?<!\d)(\d{2}(?:\.\d)?)(?!\d)",vals[icw])
                if cm:
                    try:
                        cv=float(cm.group(1))
                        if 35<=cv<=80:carried=round(cv,1)
                    except Exception:pass

            # 1) Exact body-weight column when the table aligns normally.
            if ibw>=0 and ibw<len(vals):
                weight,change=parse_weight_cell(vals[ibw])
                if weight and change is None and ichg>=0 and ichg<len(vals):
                    cm=re.search(r"([+\-]?\d{1,3})",vals[ichg])
                    if cm:
                        cv=int(cm.group(1))
                        if -99<=cv<=99:change=cv

            # 2) Layouts that render 482(+4) in one text block.
            if not weight:
                wm=re.search(r"(?<!\d)(\d{3})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]",rowtxt,re.I)
                if wm:
                    w=int(wm.group(1))
                    if 250<=w<=800:
                        weight=w;change=int(wm.group(2))

            # 3) DebaTableSmall-style rows: current weight is a standalone 3-digit
            # cell and the change is the next small integer cell.
            if not weight:
                for i,cell in enumerate(vals[:24]):
                    if not re.fullmatch(r"\d{3}",cell):continue
                    w=int(cell)
                    if not (250<=w<=800):continue
                    weight=w
                    if i+1<len(vals):
                        cm=re.fullmatch(r"\s*([+\-]?\d{1,2})\s*",vals[i+1])
                        if cm:change=int(cm.group(1))
                    break

            if not weight and carried is None:continue
            out_by_no[no]={
                "horseNumber":no,
                "bodyWeight":weight,
                "bodyWeightChange":change,
                "carriedWeight":carried,
                "source":"NAR公式出馬表",
            }

    return [out_by_no[k] for k in sorted(out_by_no)]


def _nar_official_card_rows_fast(detail:dict)->list[dict]:
    """Fetch NAR official current body weight/change from multiple official card layouts."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or ""))
    if not code:return []
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not date or not race_no:return []
    q=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":date.replace("-","/"),
        "k_raceNo":race_no,
    })
    # DebaTableSmall exposes 馬体重 / 変更 as simple columns and is the most
    # reliable source for the current value. Keep the other official layouts as fallbacks.
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/DebaTable_ipat?"+q,
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
    ]
    out_by_no={}
    # Every active runner matters. Do not stop at N-1 coverage: that caused the
    # last horse on some NAR cards to remain "未発表" even after the official
    # card had published its body weight.
    target=max(1,len([h for h in detail.get("horses",[]) or [] if not h.get("scratched")]))
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_CARD_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            print("NAR official card failed",detail.get("id"),url,exc);continue
        for row in _parse_nar_official_card_html(detail,html):
            no=int(row.get("horseNumber") or 0)
            if no:out_by_no[no]=row
        if out_by_no and (not target or len(out_by_no)>=target):break
    return [out_by_no[k] for k in sorted(out_by_no)]


def _merge_current_card_fields(detail:dict, rows:list[dict])->dict:
    if not rows:return detail
    by={int(x.get("horseNumber") or 0):x for x in rows if int(x.get("horseNumber") or 0)>0}
    changed=False
    for h in detail.get("horses",[]) or []:
        z=by.get(int(h.get("horseNumber") or 0))
        if not z:continue
        for k in ("bodyWeight","bodyWeightChange","carriedWeight","status","scratched"):
            if z.get(k) not in (None,"") and h.get(k)!=z.get(k):
                h[k]=z.get(k);changed=True
    if changed:
        detail["bodyWeightSource"]="NAR公式出馬表"
        detail["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    return detail


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


def _nar_official_result_fast(detail:dict)->dict|None:
    """Fetch NAR official RaceMarkTable directly; includes result, body weight and corner order."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or "").strip())
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not code or not date or not race_no:return None
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":date.replace("-","/"),"k_raceNo":race_no})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/RaceMarkTable_ipat?"+q,
    ]
    known={_clean(h.get("name")):int(h.get("horseNumber") or 0) for h in detail.get("horses",[]) or [] if h.get("name")}
    last_err=""
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_RESULT_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            last_err=str(exc);continue
        if not html:continue
        soup=BeautifulSoup(html,"html.parser")
        full=_clean(soup.get_text(" ",strip=True))
        if "競走成績" not in full and "着順" not in full:continue
        wm=re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)",full)
        cm=re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)",full)
        finishers=[]
        for table in soup.find_all("table"):
            rows=table.find_all("tr")
            if not rows:continue
            headers=[];header_i=-1
            for ri,tr in enumerate(rows[:4]):
                vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
                joined="|".join(vals)
                if "着順" in joined and "馬体重" in joined and "馬番" in joined:
                    headers=vals;header_i=ri;break
            if not headers:continue
            def hi(part):
                for i,x in enumerate(headers):
                    if part in x:return i
                return -1
            idx={k:hi(v) for k,v in {
                "fin":"着順","frame":"枠","no":"馬番","name":"馬名","sexage":"性齢",
                "cw":"負担","jockey":"騎手","trainer":"調教師","bw":"馬体重",
                "time":"タイム","corner":"コーナー","pop":"人気","odds":"単勝"
            }.items()}
            for tr in rows[header_i+1:]:
                cells=tr.find_all(["th","td"],recursive=False)
                vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
                if not vals:continue
                def val(key):
                    j=idx.get(key,-1)
                    return vals[j] if j>=0 and j<len(vals) else ""
                fin_txt=val("fin") or vals[0]
                mf=re.match(r"^\s*(\d+)\s*$",fin_txt)
                if not mf:continue
                fin=int(mf.group(1))
                name=val("name")
                no=0
                mno=re.search(r"\d+",val("no")) if val("no") else None
                if mno:no=int(mno.group())
                if not no and name:no=known.get(_clean(name),0)
                if not no:
                    for nm,hno in known.items():
                        if nm and nm in _clean(tr.get_text(" ",strip=True)):
                            no=hno;name=name or nm;break
                if not no:continue
                fr=0;mfr=re.search(r"\d+",val("frame")) if val("frame") else None
                if mfr:fr=int(mfr.group())
                bw=None;chg=None
                bwtxt=val("bw") or _clean(tr.get_text(" ",strip=True))
                mbw=re.search(r"(?<!\d)(\d{3,4})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]",bwtxt)
                if mbw:bw=int(mbw.group(1));chg=int(mbw.group(2))
                tm=0.0;mt=re.search(r"(\d+):(\d{2}(?:\.\d+)?)",val("time"))
                if mt:tm=int(mt.group(1))*60+float(mt.group(2))
                corners=[]
                ctext=val("corner")
                mcorn=re.search(r"(?<!\d)(\d{1,2}(?:-\d{1,2}){1,4})(?!\d)",ctext)
                if mcorn:
                    try:corners=[int(x) for x in mcorn.group(1).split("-")]
                    except Exception:corners=[]
                pop=None;mp=re.search(r"\d+",val("pop")) if val("pop") else None
                if mp:pop=int(mp.group())
                odd=None;mo=re.search(r"\d+(?:\.\d+)?",val("odds")) if val("odds") else None
                if mo:
                    try:odd=float(mo.group())
                    except Exception:odd=None
                finishers.append({
                    "finish":fin,"finishLabel":f"{fin}着","horseNumber":no,
                    "frameNumber":fr or int((no+1)//2),"name":name or next((nm for nm,hno in known.items() if hno==no),""),
                    "timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw,"bodyWeightChange":chg,
                    "popularity":pop,"winOdds":odd,
                })
            if finishers:break
        finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
        # Do not call a partial page final until at least the podium is visible.
        classified=[int(x.get("finish") or 0) for x in finishers if int(x.get("finish") or 0)>0]
        if 1 not in classified or sum(1 for finish in classified if finish<=3)<3:continue
        payouts=_parse_payouts(soup)
        explicit_final=bool(re.search(r"確定",full)) and not bool(re.search(r"速報|暫定",full))
        out={"status":"確定" if explicit_final else "速報","finishers":finishers,"source":"NAR公式競走成績","payouts":payouts}
        if wm:out["weather"]=_env_clean_weather(wm.group(1))
        if cm:out["condition"]=_env_clean_condition(cm.group(1))
        out["sourceUrl"]=url
        return out
    if last_err:print("NAR official result unavailable",detail.get("id"),last_err)
    return None


def _netkeiba_card_rows_fast(detail:dict)->list[dict]:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    try:
        html=_netkeiba_get(
            f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}",
            float(os.getenv("FAST_CARD_TIMEOUT_SEC","1.2")),20
        )
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser");rows=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        horse["source"]="netkeiba高速出走表"
        rows.append(horse)
    return rows


def _merge_card_rows_preserve(base:dict, fresh_rows:list[dict])->dict:
    """Refresh today's card fields without deleting history/metrics already collected."""
    old_horses=base.get("horses") or []
    by_no={int(h.get("horseNumber") or 0):h for h in old_horses if int(h.get("horseNumber") or 0)>0}
    by_name={str(h.get("name") or ""):h for h in old_horses if h.get("name")}
    merged=[]
    for fresh in fresh_rows or []:
        no=int(fresh.get("horseNumber") or 0)
        old=by_no.get(no) or by_name.get(str(fresh.get("name") or "")) or {}
        z=json.loads(json.dumps(old,ensure_ascii=False,default=str)) if old else {}
        for k,v in fresh.items():
            if k in {"recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                     "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace"}:
                continue
            if v not in (None,"",[],{}):z[k]=v
        # preserve rich local data
        for k in ("recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                  "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace",
                  "pedigree","representativeRun"):
            if old.get(k) not in (None,"",[],{}):z[k]=old.get(k)
        z.setdefault("recentRaces",[])
        z.setdefault("jockeyStats",{})
        z.setdefault("trainerStats",{})
        z.setdefault("jockeyProfile",{})
        z.setdefault("trainerProfile",{})
        merged.append(z)
    if merged:
        base["horses"]=merged
        base["fieldSize"]=len(merged)
    return base


def _netkeiba_past_rows_fast(detail:dict)->list[dict]:
    """One cached page gets recent runs for every JRA starter."""
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    url=f"https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}&rf=shutuba_submenu"
    try:
        html=_netkeiba_get(
            url,
            float(os.getenv("FAST_HISTORY_TIMEOUT_SEC","1.8")),
            int(os.getenv("FAST_HISTORY_CACHE_SEC","300")),
        )
    except Exception as exc:
        print("fast JRA past page failed",rid,exc);return []
    soup=BeautifulSoup(html,"html.parser");out=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        runs=[]
        for td in tr.find_all("td"):
            z=_parse_recent_cell(td.get_text(" ",strip=True))
            if z:runs.append(z)
            if len(runs)>=5:break
        horse["recentRaces"]=runs[:5]
        out.append(horse)
    return out


def _merge_fast_history(detail:dict, history_rows:list[dict])->dict:
    by_no={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    by_name={str(h.get("name") or ""):h for h in detail.get("horses",[]) or [] if h.get("name")}
    for row in history_rows or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or ""))
        if not h:continue
        runs=list(row.get("recentRaces") or [])
        if runs:
            old=list(h.get("allPastRuns") or h.get("recentRaces") or [])
            merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))
            h["recentRaces"]=merged[:5]
            h["allPastRuns"]=merged
    return detail


def _hydrate_fast_card_now(race_id:str, deep_history:bool=False)->None:
    # NAR: hydrate the date once. v117 called a non-existent sync_day(), so selected
    # local races could stay empty until another background job happened to fill the DB.
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m:return
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        sync=None
        try:
            target=datetime.strptime(iso_date,"%Y-%m-%d").date()
            sync=NarSync()
            with _nar_sync_io_lock:
                if iso_date==_today_iso():sync.sync_daily(force=False)
                else:sync.sync_month(target.year,target.month,force=False)
        except Exception as exc:
            print("fast NAR date hydrate failed",race_id,exc)
        finally:
            try:
                if sync:sync.store.conn.close()
            except Exception:pass
        q=_fast_local_race_detail(race_id)
        if q:
            # Finished/started races: RaceMarkTable is the fastest authoritative source and also
            # carries body weight. Before the race, use the official card from multiple layouts.
            official_result=None
            if _nar_result_should_be_available(q):
                try:official_result=_nar_official_result_fast(q)
                except Exception as exc:print("fast NAR official result failed",race_id,exc)
            if official_result:
                q["result"]=official_result
                if official_result.get("weather") not in (None,"","不明"):q["weather"]=official_result["weather"]
                if official_result.get("condition") not in (None,"","不明"):q["condition"]=official_result["condition"]
                q=_merge_result_fields(q,official_result)
                q["bodyWeightSource"]="NAR公式競走成績"
                q["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
            else:
                try:q=_merge_current_card_fields(q,_nar_official_card_rows_fast(q))
                except Exception as exc:print("fast NAR official body weight failed",race_id,exc)
            _store_fast_snapshot(q)
            if deep_history:
                names=[str(h.get("name") or "") for h in q.get("horses",[]) if h.get("name")]
                cov=_history_counts(names,iso_date)
                if names and not _history_is_enough(cov,0):
                    _start_race_history_search(race_id,iso_date,names,force=False)
        return

    m=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",race_id)
    if not m:return
    date,track,rno=m.group(1),m.group(2),int(m.group(3))
    base=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:base=json.loads(row["payload"])
                except Exception:base=None
        finally:conn.close()
    if not base:
        base={"id":race_id,"circuit":"中央","date":date,"track":track,"raceNumber":rno,
              "title":f"{rno}R","distance":0,"surface":"","condition":"不明","weather":"不明",
              "horses":[],"source":"高速出走表"}

    rows=_netkeiba_card_rows_fast(base)
    if rows:
        base=_merge_card_rows_preserve(base,rows)
        base["id"]=race_id;base["circuit"]="中央"
        # Weather/going is a separate lightweight feed; do not let the fast
        # horse-card path leave the race at "不明".
        if date==_today_iso() and (base.get("weather") in (None,"","不明") or base.get("condition") in (None,"","不明")):
            try:
                env=_jra_fetch_environment(base)
                if env.get("weather") not in (None,"","不明"):base["weather"]=env["weather"]
                if env.get("condition") not in (None,"","不明"):base["condition"]=env["condition"]
                if env:base["environmentMeta"]={"source":env.get("source","JRA公式優先"),"updatedAtEpoch":env.get("updatedAtEpoch",int(time.time()))}
            except Exception as exc:print("fast JRA environment failed",race_id,exc)
        # One past page hydrates all starters; collector does this before the customer taps.
        if not _diagnosis_history_quality(base).get("ready"):
            base=_merge_fast_history(base,_netkeiba_past_rows_fast(base))
        try:
            st=CentralStore();st.upsert([base]);st.conn.close()
        except Exception as exc:print("fast card central save failed",exc)
        try:RACEDB.upsert_race(base)
        except Exception as exc:print("fast card racedb save failed",exc)
        q=_fast_local_race_detail(race_id)
        if q:_store_fast_snapshot(q)
        return

    # Official fallback only after the faster single-page route fails.
    try:
        cname=_jra_find_cname(date,track,rno)
        live=_jra_parse_race(cname,supplement_profiles=False) if cname else None
        if live:
            live["id"]=race_id
            st=CentralStore();st.upsert([live]);st.conn.close()
            q=_fast_local_race_detail(race_id)
            if q:_store_fast_snapshot(q)
    except Exception as exc:print("fast JRA card hydrate failed",race_id,exc)

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

def _bootstrap_display_ready(d:dict|None)->bool:
    """Enough data to open/render the race immediately."""
    if not isinstance(d,dict):return False
    return bool((d.get("horses") or []) or d.get("result"))

def _bootstrap_analysis_ready(d:dict|None)->bool:
    """Diagnosis readiness is tracked separately and must never block site display."""
    if not _bootstrap_display_ready(d):return False
    if _snapshot_final(d):return True
    pm=d.get("preparedMeta") or {}
    return bool(pm.get("diagnosisReady") and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION)

# Compatibility for older internal callers: "ready" now means display-ready.
def _bootstrap_detail_ready(d:dict|None)->bool:
    return _bootstrap_display_ready(d)

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
            if total == 0 or resolved >= total:
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












