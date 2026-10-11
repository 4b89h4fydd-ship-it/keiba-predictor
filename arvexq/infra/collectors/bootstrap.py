"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _site_bootstrap_warm_loop(*, _schedule_day_bundle_refresh, _today_iso, os, time):
    time.sleep(float(os.getenv('BOOTSTRAP_START_DELAY_SEC', '2.5')))
    while True:
        try:
            _schedule_day_bundle_refresh(_today_iso(), False)
        except Exception as exc:
            print('bundle warmer failed', exc)
        time.sleep(max(20, int(os.getenv('BOOTSTRAP_REFRESH_SEC', '30'))))

def _start_site_bootstrap_warmer(*, _site_bootstrap_warm_loop, os, threading):
    enabled = str(os.getenv('ARVEXQ_BOOTSTRAP_WARM', '1')).lower() in {'1', 'true', 'yes', 'on'}
    if enabled:
        threading.Thread(target=_site_bootstrap_warm_loop, daemon=True, name='arvexq-bootstrap').start()
