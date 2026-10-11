"""Feature-owned cache and lock; TTL and invalidation remain with callers."""
import threading

_detail_cache_lock=threading.Lock()
_detail_cache:dict[str,tuple[float,dict]]={}
