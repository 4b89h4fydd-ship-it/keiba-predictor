"""Feature-owned state; no worker is started at import time."""
import threading

_live_refresh_lock = threading.Lock()
_live_refresh_last: dict[str, int] = {}
_live_refresh_running: set[str] = set()
_central_refresh_lock = threading.Lock()
_central_refresh_running: set[str] = set()
_central_refresh_last: dict[str, int] = {}
