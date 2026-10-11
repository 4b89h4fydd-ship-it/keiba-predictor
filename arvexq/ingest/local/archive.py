"""local/archive: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.scheduling import iter_months_back
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datetime import datetime
from pathlib import Path
import io
import os
import time
import urllib.parse
import urllib.request
import zipfile


from arvexq.ingest.local.state import _nar_sync_io_lock

def sync_recent_history(months: int=12, *, NarSync) -> list[dict]:
    sync = NarSync()
    out = []
    today = datetime.now().date()
    for year, month in reversed(list(iter_months_back(today, months))):
        out.append(sync.sync_month(year, month))
    return out


def _nar_month_needs_fetch(year: int, month: int, *, NarStore) -> bool:
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


def _download_nar_month_only(year: int, month: int, *, ARCHIVE_DIR, NAR_MONTHLY_RACE_URL) -> tuple[int, int, bytes, Path]:
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


def _sync_nar_month_wave(months: list[tuple[int, int]], *, NarSync, _download_nar_month_only, _nar_month_needs_fetch) -> tuple[list[dict], list[str]]:
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
