"""Feature-owned cache and lock; TTL and invalidation remain with callers."""
import threading

_race_list_cache_lock = threading.Lock()
_race_list_cache: dict[str, tuple[float, list[dict]]] = {}
