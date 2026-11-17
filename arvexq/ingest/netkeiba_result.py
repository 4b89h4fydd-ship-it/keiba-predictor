"""Parse factual race results from an observed netkeiba HTML response."""
from __future__ import annotations
import re
from typing import Callable, Any

from bs4 import BeautifulSoup


def _clock_seconds(token: str) -> float | None:
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", token.strip())
    if not m:
        return None
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def _parse_race_lap_times(soup) -> list[float]:
    """Segment lap times (per 200m) from the result page's ラップタイム
    table. Two layouts exist: the smartphone table carries
    "<cumulative> <lap>" pairs in each cell (the lap is the second
    number); the desktop table carries a cumulative row followed by
    a lap row of single numbers (cross-checked against the
    cumulative differences). Returns [] when the table is absent or
    any cell is unparsable — partial laps are not published as
    fact."""
    for tb in soup.find_all("table"):
        rows = []
        is_lap_table = False
        for tr in tb.find_all("tr"):
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["th", "td"])]
            if any(re.fullmatch(r"\d+m", c.replace(" ", "")) for c in cells):
                is_lap_table = True
                continue
            if is_lap_table:
                rows.append(cells)
        if not is_lap_table:
            continue
        pair_laps: list[float] = []
        pair_ok = True
        single_rows: list[list[float]] = []
        for cells in rows:
            values = [c for c in cells if c.strip()]
            if not values:
                continue
            parts = [c.replace("　", " ").split() for c in values]
            if all(len(p) == 2 for p in parts):
                for p in parts:
                    lap = _clock_seconds(p[1])
                    if lap is None or not (5.0 <= lap <= 30.0):
                        pair_ok = False
                        break
                    pair_laps.append(lap)
                if not pair_ok:
                    break
            elif all(len(p) == 1 for p in parts):
                nums = [_clock_seconds(p[0]) for p in parts]
                if all(n is not None for n in nums):
                    single_rows.append(nums)
        if pair_ok and len(pair_laps) >= 2:
            return pair_laps
        if len(single_rows) >= 2:
            cumulative, laps = single_rows[0], single_rows[-1]
            if (len(cumulative) == len(laps)
                    and all(5.0 <= lap <= 30.0 for lap in laps)):
                diffs = [cumulative[0]] + [
                    round(cumulative[i] - cumulative[i - 1], 2)
                    for i in range(1, len(cumulative))]
                if all(abs(d - lap) <= 0.15
                       for d, lap in zip(diffs, laps)):
                    return laps
    return []


def parse_current_result_html(
    html: str,
    *,
    clean: Callable[[Any], str],
    parse_time_seconds: Callable[[str], float],
    parse_payouts: Callable[[BeautifulSoup], list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Parse runner result facts from HTML; network access remains with caller."""
    if not html:
        return None
    soup=BeautifulSoup(html,"html.parser"); table=None; headers=[]
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr")[:4]:
            vals=[re.sub(r"\s+","",clean(c.get_text(" ",strip=True))) for c in tr.find_all(["th","td"])]
            if any("着順" in v for v in vals) and any("馬番" in v for v in vals) and any("馬名" in v for v in vals):
                table=tb;headers=vals;break
        if table:break
    if table is None:return None
    def hidx(*keys):
        for i,v in enumerate(headers):
            for k in keys:
                if k in v:return i
        return -1
    i_fin=hidx("着順");i_frame=hidx("枠");i_no=hidx("馬番");i_name=hidx("馬名");i_time=hidx("タイム");i_margin=hidx("着差");i_corner=hidx("コーナー通過順");i_pop=hidx("人気");i_odds=hidx("単勝オッズ","単勝");i_bw=hidx("馬体重");i_last3f=hidx("後3F","上がり","上り")
    finishers=[]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if not tds:continue
        vals=[clean(td.get_text(" ",strip=True)) for td in tds]
        def val(i):return vals[i] if 0<=i<len(vals) else ""
        fm=re.search(r"\d+",val(i_fin)) if i_fin>=0 else None
        fin=int(fm.group()) if fm else 0; no=0; frame=0
        mn=re.search(r"\d+",val(i_no)) if i_no>=0 else None
        mf=re.search(r"\d+",val(i_frame)) if i_frame>=0 else None
        if mn:no=int(mn.group())
        if mf:frame=int(mf.group())
        if not no:
            um=tr.find("td",class_=re.compile(r"Umaban",re.I))
            mm=re.search(r"\d+",clean(um.get_text(" ",strip=True))) if um else None
            if mm:no=int(mm.group())
        name=val(i_name)
        if not name:
            na=tr.select_one(".Horse_Name a,.HorseInfo a,.Horse_Name")
            name=clean(na.get_text(" ",strip=True)) if na else ""
        tm=parse_time_seconds(val(i_time)) if i_time>=0 else 0.0
        margin=val(i_margin).strip() if i_margin>=0 else ""
        if i_margin<0 and i_time>=0:
            # The smartphone layout has no 着差 column either: the
            # margin rides inside the time cell as
            # "<time> <margin> (<last 3F>)", e.g. "1:13.4 1 (37.0)" or
            # "1:14.2 アタマ (37.5)"; the winner's cell carries no
            # margin token ("1:13.3 (36.7)"), matching the official
            # table's empty winner margin. Without this, every finisher
            # parsed through the fallback stored no marginText at all
            # (the same Kyoto/Tokyo results hit by the popularity drop).
            mt=re.match(r"^\s*(?:\d{1,2}:)?\d{1,2}(?:\.\d+)?\s*(.*?)\s*(?:\([^)]*\)\s*)?$",val(i_time))
            if mt:
                cand=mt.group(1).strip()
                if cand and len(cand)<=8 and ":" not in cand and "(" not in cand:
                    margin=cand
        corners=[]
        cs=val(i_corner)
        cm=re.search(r"\d{1,2}(?:-\d{1,2})+",cs)
        if cm:corners=[int(x) for x in cm.group().split("-")]
        pop=None;odd=None;bw=None;chg=None
        mp=re.search(r"\d+",val(i_pop)) if i_pop>=0 else None
        if mp:
            try:pop=int(mp.group())
            except Exception:pass
        mo=re.search(r"\d+(?:\.\d+)?",val(i_odds)) if i_odds>=0 else None
        if mo:
            try:odd=float(mo.group())
            except Exception:pass
        if pop is None or odd is None:
            # The smartphone layout (the default fetch UA) has no 人気
            # column at all: the odds cell carries both facts as one
            # string, e.g. "2.7倍 1人気". Without this, every finisher
            # parsed through the fallback stored popularity=None (the
            # 2026-11-07/08 Kyoto/Tokyo results), which silently blocked
            # every market-relative measurement for those races.
            for cell in vals:
                cm=re.search(r"(\d+(?:\.\d+)?)\s*倍\s*(\d+)\s*人気",cell)
                if cm:
                    if odd is None:
                        try:odd=float(cm.group(1))
                        except Exception:pass
                    if pop is None:
                        try:pop=int(cm.group(2))
                        except Exception:pass
                    break
        mb=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",val(i_bw)) if i_bw>=0 else None
        if mb:
            try:bw=int(mb.group(1));chg=int(mb.group(2)) if mb.group(2) is not None else None
            except Exception:pass
        # 上がり3F (last 3F): the desktop layout carries a dedicated
        # 上がり column; the smartphone layout embeds the value in the
        # time cell as a trailing parenthesis ("1:54.4 (39.4)" /
        # "1:54.7 1.3/4 (39.3)") — the same parenthesis the margin
        # fallback above already skips over. Capture it instead of
        # discarding it; an absent or unparsable value stays absent
        # (never estimated). Both key spellings are emitted because
        # downstream consumers split between them (career/history use
        # last3fSeconds; the central-run builder uses last3FSeconds).
        last3f=None
        if i_last3f>=0:
            lm=re.fullmatch(r"\d{1,2}\.\d{1,2}",val(i_last3f).strip())
            if lm:
                try:last3f=float(lm.group())
                except Exception:last3f=None
        if last3f is None and i_time>=0:
            pm=re.search(r"\((\d{1,2}\.\d{1,2})\)\s*$",val(i_time).strip())
            if pm:
                try:last3f=float(pm.group(1))
                except Exception:last3f=None
        if last3f is not None and not (15.0<=last3f<=90.0):last3f=None
        finisher={"finish":fin,"finishLabel":str(fin)+"着" if fin else val(i_fin),"horseNumber":no,"frameNumber":frame,"name":name,"timeSeconds":tm,"marginText":margin,"cornerPositions":corners,"winOdds":odd,"popularity":pop,"bodyWeight":bw,"bodyWeightChange":chg}
        if last3f is not None:
            finisher["last3fSeconds"]=last3f
            finisher["last3FSeconds"]=last3f
        if no and name:finishers.append(finisher)
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    if len(finishers)<3:return None
    payouts=parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",clean(soup.get_text(" ",strip=True))) else "速報"
    result={"status":status,"finishers":finishers,"source":"netkeiba結果","payouts":payouts}
    laps=_parse_race_lap_times(soup)
    if laps:
        # Whole-race segment laps (not per-horse), same semantics as
        # the NAR公式CSV raceLapTimes the career builder stores.
        result["raceLapTimes"]=laps
    return result
