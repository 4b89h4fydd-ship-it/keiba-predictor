"""Shared per-race progress; provider network locks and caches are separate."""
import threading

_race_history_lock = threading.Lock()
_race_history_jobs: dict[str, dict] = {}

_full_history_lock=threading.Lock()

_full_history_running:set[str]=set()
