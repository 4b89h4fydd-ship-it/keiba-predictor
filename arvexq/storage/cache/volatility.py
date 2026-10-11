"""Feature-owned cache and lock; TTL and invalidation remain with callers."""
import threading

_volatility_pack_lock=threading.Lock()
_volatility_pack_cache:dict[str,tuple[float,list[dict]]]={}
