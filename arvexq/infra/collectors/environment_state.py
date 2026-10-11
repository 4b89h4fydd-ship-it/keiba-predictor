"""Feature-owned state; no worker is started at import time."""
import threading

_environment_lock=threading.Lock()
_environment_running:set[str]=set()
_environment_state:dict[str,dict]={}
