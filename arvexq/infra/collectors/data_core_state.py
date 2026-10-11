"""Feature-owned state; no worker is started at import time."""
import threading

_data_core_lock=threading.Lock()
_data_core_running:set[str]=set()
_data_core_state={"running":False,"lastStart":0,"lastFinish":0,"checked":0,"refreshed":0,"error":""}
