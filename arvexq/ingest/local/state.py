"""Source-owned cache and synchronization state; no I/O on import.

Cache TTLs and failed/empty result handling remain in the owning operations.
The app aliases exist for legacy callers; these objects are initialized here.
"""
import re
import threading

_nar_sync_io_lock = threading.Lock()
NAR_BABA_CODES={"帯広ば":"03","帯広":"03","盛岡":"10","水沢":"11","浦和":"18","船橋":"19","大井":"20","川崎":"21","金沢":"22","笠松":"23","名古屋":"24","園田":"27","姫路":"28","高知":"31","佐賀":"32","門別":"36"}
NAR_NETKEIBA_CODES={"門別":"30","盛岡":"35","水沢":"36","浦和":"42","船橋":"43","大井":"44","川崎":"45","金沢":"46","笠松":"47","名古屋":"48","園田":"50","姫路":"51","高知":"54","佐賀":"55"}
_nar_odds_cache_lock=threading.Lock()
_nar_odds_cache:dict[str,tuple[float,dict]]={}
