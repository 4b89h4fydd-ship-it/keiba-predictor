"""Source-owned cache and synchronization state; no I/O on import.

Cache TTLs and failed/empty result handling remain in the owning operations.
The app aliases exist for legacy callers; these objects are initialized here.
"""
import re
import threading

JRA_TRACK_CODES = {"01":"札幌","02":"函館","03":"福島","04":"新潟","05":"東京","06":"中山","07":"中京","08":"京都","09":"阪神","10":"小倉"}
JRA_TRACK_CODE_BY_NAME = {v:k for k,v in JRA_TRACK_CODES.items()}
JRA_MEETING_DAY_RE = re.compile(r"(\d+)回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)(\d+)日")
JRA_CNAME_RE = re.compile(r"pw01dde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_HORSE_CNAME_RE = re.compile(r"pw01dud\d{12,}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
JRA_RESULT_CNAME_RE = re.compile(r"pw01sde(?:01|10)\d{20}(?:/|%2F)[0-9A-Fa-f]{2}",re.I)
_jra_cache_lock = threading.Lock()
_jra_text_cache: dict[str, tuple[float,str]] = {}
JRA_BAD_TITLE_RE = re.compile(r"検索ウィンドウ|緊急情報|重要なお知らせ|お知らせ|関連メニュー|今週の開催|JRAからのお知らせ|インフォメーション|ピックアップ|発売レース|各種サービス|スペシャルコンテンツ|競馬メニュー|開催日程")
JRA_PROGRAM_TRACK_RE = re.compile(r"\d+回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\d+日")
_jra_program_cache_lock=threading.Lock()
_jra_program_cache={}
_jra_cname_lookup_lock=threading.Lock()
_jra_cname_lookup={}
