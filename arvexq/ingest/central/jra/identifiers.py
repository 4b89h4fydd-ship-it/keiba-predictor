"""central/jra/identifiers: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
import re


from arvexq.ingest.central.jra.state import JRA_TRACK_CODES
from arvexq.ingest.central.jra.state import JRA_RESULT_CNAME_RE

def _jra_norm_cname(value: str) -> str:
    return re.sub(r"%2F","/",str(value or ""),flags=re.I)


def _jra_attr_cname(tag, pattern, *, _jra_norm_cname) -> str:
    if not tag: return ""
    blob=" ".join(str(v) for v in tag.attrs.values())+" "+str(tag)
    m=pattern.search(blob)
    return _jra_norm_cname(m.group(0)) if m else ""


def _jra_program_title(info: str) -> str:
    s=re.sub(r"\s+"," ",str(info or "")).strip(); dm=re.search(r"[\d,]{4,5}\s*[（(]",s); prefix=(s[:dm.start()] if dm else s).strip()
    cm=re.search(r"\s+(?:障害)?(?:2歳|3歳|4歳)(?:以上)?",prefix)
    if cm and cm.start()>0:
        named=prefix[:cm.start()].strip()
        if named:return named
    return prefix


def _jra_text(tag) -> str:
    return re.sub(r"\s+"," ",tag.get_text(" ",strip=True) if tag else "").strip()


def _jra_iso_date(y: int, m: int, d: int) -> str:
    return f"{y:04d}-{m:02d}-{d:02d}"


def _jra_date_from_cname(cname: str) -> str:
    m=re.search(r"(20\d{6})/[0-9A-Fa-f]{2}$",cname or "")
    if not m:return ""
    x=m.group(1);return f"{x[:4]}-{x[4:6]}-{x[6:8]}"


def _jra_race_no_from_cname(cname: str) -> int:
    m=re.search(r"pw01dde(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "")
    return int(m.group(1)) if m else 0


def _jra_track_from_cname(cname: str) -> str:
    m=re.search(r"pw01dde(?:01|10)(\d{2})",cname or "")
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""


def _jra_parse_time_seconds(txt: str) -> float:
    m=re.search(r"(?<!\d)(\d{1,2}):(\d{2}\.\d)(?!\d)",txt or "")
    if not m:return 0.0
    return int(m.group(1))*60+float(m.group(2))


def _jra_result_cname_from_card(cname: str, *, _jra_norm_cname, _jra_request) -> str:
    if not cname:return ""
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20)
    except Exception as exc:
        print("JRA result link fetch failed",exc);return ""
    vals=[_jra_norm_cname(x) for x in JRA_RESULT_CNAME_RE.findall(html)]
    return vals[0] if vals else ""


def _jra_any_track(cname: str) -> str:
    m=re.search(r"pw01(?:d|s)de(?:01|10)(\d{2})",cname or "",re.I)
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""


def _jra_any_race_no(cname: str) -> int:
    m=re.search(r"pw01(?:d|s)de(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "",re.I)
    return int(m.group(1)) if m else 0
