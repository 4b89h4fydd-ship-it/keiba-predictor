"""Source-owned cache and synchronization state; no I/O on import.

Cache TTLs and failed/empty result handling remain in the owning operations.
The app aliases exist for legacy callers; these objects are initialized here.
"""
import re
import threading

_smart_cache_lock=threading.Lock()
_smart_cache:dict[str,tuple[float,dict]]={}
