"""Feature-owned state; no worker is started at import time."""
import threading

_auto_odds_lock=threading.Lock()
_auto_odds_last:dict[str,float]={}
_auto_odds_state={"running":False,"lastStart":0,"lastFinish":0,"checked":0,"updated":0,"error":""}
