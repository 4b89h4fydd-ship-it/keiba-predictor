"""Source-owned cache and synchronization state; no I/O on import.

Cache TTLs and failed/empty result handling remain in the owning operations.
The app aliases exist for legacy callers; these objects are initialized here.
"""
import re
import threading

NETKEIBA_TRACK_CODES={"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
_netkeiba_cache_lock=threading.Lock()
_netkeiba_cache={}
