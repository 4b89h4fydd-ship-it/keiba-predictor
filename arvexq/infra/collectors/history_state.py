"""Feature-owned state; no worker is started at import time."""
import threading

_history_lock = threading.Lock()
_history_started = False
_history_ready = False
_history_error = ""
