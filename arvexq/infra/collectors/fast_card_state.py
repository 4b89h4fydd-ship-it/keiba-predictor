"""Feature-owned state; no worker is started at import time."""
import threading

_racedb_refresh_lock=threading.Lock()
_racedb_refresh_running:set[str]=set()
_fast_card_lock=threading.Lock()
_fast_card_running:set[str]=set()
_fast_card_pending:set[str]=set()
_fast_card_queue=[]
_fast_card_cv=threading.Condition()
_fast_card_workers_started=False
