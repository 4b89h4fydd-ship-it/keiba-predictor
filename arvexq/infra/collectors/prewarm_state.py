"""Feature-owned state; no worker is started at import time."""
import threading

_prewarm_lock = threading.Lock()
_prewarm_running: set[str] = set()
_prewarm_state: dict[str, dict] = {}
