"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _prediction_clock_state(detail: dict) -> tuple[str, int | None]:
    """Return (state, minutes_to_post). Never infer a lock after the race has started."""
    d=str((detail or {}).get("date") or "")
    st=str((detail or {}).get("startTime") or (detail or {}).get("scheduledStartTime") or "")
    if not d:return "unknown",None
    today=_today_iso()
    if d<today:return "started",None
    if d>today:return "future",None
    m=re.match(r"^(\d{1,2}):(\d{2})",st)
    if not m:return "unknown",None
    post=int(m.group(1))*60+int(m.group(2));now=_now_jst();nowm=now.hour*60+now.minute
    return ("pre" if nowm<post else "started"),post-nowm
