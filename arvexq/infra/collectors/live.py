"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _schedule_live_refresh(iso_date: str, force: bool=False, *, NarSync, _live_refresh_last, _live_refresh_lock, _live_refresh_running, _nar_sync_io_lock, _race_list_cache, _race_list_cache_lock, _today_iso, datetime, threading, time):
    key = f'live:{iso_date}'
    now = int(time.time())
    with _live_refresh_lock:
        if key in _live_refresh_running or (not force and now - _live_refresh_last.get(key, 0) < 90):
            return
        _live_refresh_running.add(key)

    def worker():
        changed = False
        try:
            try:
                target = datetime.strptime(iso_date, '%Y-%m-%d').date()
                sync = NarSync()
                with _nar_sync_io_lock:
                    if iso_date == _today_iso():
                        sync.sync_daily(force=force)
                    else:
                        sync.sync_month(target.year, target.month, force=force)
                changed = True
            except Exception as exc:
                print(f'NAR background sync failed: {exc}')
            if changed:
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k, None) for k in list(_race_list_cache) if k.startswith(iso_date + '|')]
        finally:
            with _live_refresh_lock:
                _live_refresh_running.discard(key)
                _live_refresh_last[key] = int(time.time())
    threading.Thread(target=worker, daemon=True).start()

def _schedule_central_refresh(iso_date: str, force: bool=False, *, CentralStore, _central_refresh_last, _central_refresh_lock, _central_refresh_running, _clean, _netkeiba_race_summaries, _race_list_cache, _race_list_cache_lock, _today_iso, fetch_central_feed, fetch_jra_official, os, threading, time):
    now = int(time.time())
    with _central_refresh_lock:
        if iso_date in _central_refresh_running:
            return
        ttl = 90 if iso_date == _today_iso() else 3600
        if not force and now - _central_refresh_last.get(iso_date, 0) < ttl:
            return
        _central_refresh_running.add(iso_date)

    def worker():
        success = False
        try:
            if _clean(os.getenv('CENTRAL_FEED_URL', '')):
                rows = fetch_central_feed(iso_date)
            else:
                rows = fetch_jra_official(iso_date, lightweight=True)
                if not rows:
                    rows = _netkeiba_race_summaries(iso_date)
            if rows:
                st = CentralStore()
                try:
                    st.upsert(rows)
                finally:
                    st.conn.close()
                success = True
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k, None) for k in list(_race_list_cache) if k.startswith(iso_date + '|')]
        except Exception as exc:
            print(f'Central async refresh failed: {exc}')
        finally:
            with _central_refresh_lock:
                _central_refresh_running.discard(iso_date)
                _central_refresh_last[iso_date] = int(time.time()) if success else max(0, int(time.time()) - 85)
    threading.Thread(target=worker, daemon=True).start()
