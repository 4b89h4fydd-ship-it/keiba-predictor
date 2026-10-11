"""Feature-owned state; no worker is started at import time."""
import threading

_site_bootstrap_lock=threading.Lock()
_site_bootstrap_build_lock=threading.Lock()
_site_bootstrap_cache:dict[str,tuple[float,dict]]={}
_site_force_cache:dict[str,tuple[float,dict]]={}
_site_bootstrap_state:dict[str,dict]={}
