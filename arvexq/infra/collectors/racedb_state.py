"""Feature-owned state; no worker is started at import time."""
import threading

_racedb_daemon_started=False
_racedb_daemon_lock=threading.Lock()
