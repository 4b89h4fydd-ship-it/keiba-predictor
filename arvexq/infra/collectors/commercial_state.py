"""Feature-owned state; no worker is started at import time."""
import threading

_commercial_collector_lock=threading.Lock()
_commercial_collector_state={
    "running":False,"lastStart":0,"lastFinish":0,"lastError":"",
    "hydrated":0,"diagnosed":0,"cycleSec":0,
}
