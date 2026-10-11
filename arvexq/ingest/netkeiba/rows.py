"""netkeiba/rows: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.scalars import _clean
from arvexq.normalize.scalars import _scratch_status
import re


def _nk_row_horse_no(tr, index: int | None=None, *, _NK_ODDS_ID_RE) -> int:
    """netkeiba HorseList 行の馬番。

    現行DOMは馬番セルが無く、オッズ span の id (odds-1_01) と行順が馬番を持つ。
    旧DOMは td.Umaban に馬番があったため両対応にする。
    """
    o = tr.find("span", id=_NK_ODDS_ID_RE)
    if o is not None:
        m = _NK_ODDS_ID_RE.match(str(o.get("id") or ""))
        if m and int(m.group(1)) > 0:
            return int(m.group(1))
    um = tr.find("td", class_=re.compile(r"^Umaban"))
    if um is not None:
        m = re.search(r"\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and int(m.group()) > 0:
            return int(m.group())
    if index is not None:
        return int(index) + 1
    return 0


def _nk_row_frame(tr, *, _NK_WAKU_RE) -> int:
    for td in tr.find_all("td"):
        for cls in (td.get("class") or []):
            m = _NK_WAKU_RE.match(str(cls))
            if m:
                return int(m.group(1))
    return 0


def _nk_row_horse(tr, index: int | None=None, *, _NK_SEXAGE_RE, _nk_row_frame, _nk_row_horse_no) -> dict | None:
    """netkeiba HorseList 1行 -> 出走馬 dict。旧DOM/新DOM両対応。"""
    info = tr.select_one("td.Horse_Info") or tr.select_one("td.HorseInfo")
    if info is None:
        return None
    name_a = (info.select_one("dt.Horse a") or info.select_one("div.Horse02 a")
              or info.select_one("dt a") or info.select_one(".HorseName a"))
    name = _clean(name_a.get_text(" ", strip=True)) if name_a else ""
    if not name or "のデータベース" in name or len(name) > 24:
        return None
    no = _nk_row_horse_no(tr, index)
    if no <= 0:
        return None

    sex = ""; age = 0
    barei = _clean(tr.select_one("span.Barei").get_text(" ", strip=True)) if tr.select_one("span.Barei") else ""
    if not barei:
        bt = tr.select_one("td.Barei")
        barei = _clean(bt.get_text(" ", strip=True)) if bt else ""
    if not barei:
        dd_age = info.select_one("dd.Age")
        if dd_age is not None:
            barei = _clean(dd_age.get_text(" ", strip=True))
    m = _NK_SEXAGE_RE.match(barei)
    if m:
        sex = m.group(1); age = int(m.group(2))

    jockey = ""; carried = 0.0
    dd_j = info.select_one("dd.Jockey")
    if dd_j is not None:
        em = dd_j.find("em")
        jockey = _clean(em.get_text(" ", strip=True)) if em else ""
        jtxt = _clean(dd_j.get_text(" ", strip=True))
        if not jockey:
            jockey = _clean(re.sub(r"[\d.]+", " ", jtxt))
        m = re.search(r"(\d{2}(?:\.\d)?)\s*$", jtxt)
        if m:
            try: carried = float(m.group(1))
            except Exception: carried = 0.0
    if not jockey or not carried:
        jt = tr.select_one("td.Jockey")
        if jt is not None:
            ja = jt.find("a")
            if ja is not None and not jockey:
                jockey = _clean(ja.get_text(" ", strip=True))
            jtxt = _clean(jt.get_text(" ", strip=True))
            m = re.search(r"(\d{2}(?:\.\d)?)\s*$", jtxt)
            if m and not carried:
                try: carried = float(m.group(1))
                except Exception: carried = 0.0

    trainer = ""
    tr_el = tr.select_one("td.Trainer")
    if tr_el is not None:
        trainer = _clean(tr_el.get_text(" ", strip=True))
    if not trainer:
        for sel in ("div.Horse05 a", "div.Horse05"):
            el = info.select_one(sel)
            if el is None:
                continue
            t = re.sub(r"^(栗東|美浦|地方|外国)\s*[・･]\s*", "", _clean(el.get_text(" ", strip=True)))
            if t:
                trainer = t
                break

    wtxt = ""
    wt = tr.select_one("td.Weight")
    if wt is not None:
        wtxt = _clean(wt.get_text(" ", strip=True))
    if not wtxt:
        wt = info.select_one("div.Weight")
        if wt is not None:
            wtxt = _clean(wt.get_text(" ", strip=True))
    bw = None; chg = None
    m = re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?", wtxt)
    if m:
        try:
            bw = int(m.group(1))
            chg = int(m.group(2)) if m.group(2) is not None else None
        except Exception:
            bw = None; chg = None

    odds = None; pop = None
    o = tr.find("span", id=re.compile(r"^odds-1_"))
    if o is not None:
        m = re.search(r"\d+(?:\.\d+)?", _clean(o.get_text(" ", strip=True)))
        if m:
            try: odds = float(m.group())
            except Exception: odds = None
    p = tr.find("span", id=re.compile(r"^ninki-1_"))
    if p is not None:
        m = re.search(r"\d+", _clean(p.get_text(" ", strip=True)))
        if m: pop = int(m.group())

    txt = _clean(tr.get_text(" ", strip=True))
    status = _scratch_status(txt)
    return {
        "horseNumber": no,
        "frameNumber": _nk_row_frame(tr) or int((no + 1) // 2),
        "name": name, "sex": sex, "age": age,
        "carriedWeight": carried, "jockey": jockey, "trainer": trainer,
        "bodyWeight": bw, "bodyWeightChange": chg,
        "winOdds": odds, "popularity": pop,
        "status": status, "scratched": bool(status),
        "recentRaces": [],
        "jockeyStats": {}, "trainerStats": {}, "jockeyProfile": {}, "trainerProfile": {},
        "source": "netkeiba",
    }
