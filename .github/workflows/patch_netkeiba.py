#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ v324 netkeiba 出走表パーサ修正パッチ

netkeiba の HTML 構造変更（td.HorseInfo -> td.Horse_Info, td.Umaban 廃止 など）に
追随できておらず、中央(JRA)レースの出走表が「馬名空・馬番0・数頭のみ」になっていた
問題を修正する。

- 馬番: span#odds-1_XX の接尾辞（無ければ行順）
- 馬名: td.Horse_Info dt.Horse a / div.Horse02 a
- 性齢: dd.Age / td.Jockey span.Barei
- 騎手: dd.Jockey a em / td.Jockey a
- 斤量: dd.Jockey 末尾の数値 / td.Jockey span
- 調教師: div.Horse05 a（現行DOMは出走表本表に調教師列が無い）
- 馬体重: td.Weight / div.Weight
- 枠番: 先頭 td の WakuN クラス
旧DOM・新DOM の両対応にして後方互換を保つ。
"""
from pathlib import Path

SRC = Path(__file__).resolve().parent / "app.py"
text = SRC.read_text(encoding="utf-8")
before = len(text)

HELPER = '''
_NK_WAKU_RE = re.compile(r"^Waku(\\d)$")
_NK_ODDS_ID_RE = re.compile(r"^odds-1_(\\d{1,2})$")
_NK_SEXAGE_RE = re.compile(r"^(牡|牝|セ|騸)\\s*(\\d{1,2})")


def _nk_row_horse_no(tr, index: int | None = None) -> int:
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
        m = re.search(r"\\d{1,2}", _clean(um.get_text(" ", strip=True)))
        if m and int(m.group()) > 0:
            return int(m.group())
    if index is not None:
        return int(index) + 1
    return 0


def _nk_row_frame(tr) -> int:
    for td in tr.find_all("td"):
        for cls in (td.get("class") or []):
            m = _NK_WAKU_RE.match(str(cls))
            if m:
                return int(m.group(1))
    return 0


def _nk_row_horse(tr, index: int | None = None) -> dict | None:
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
            jockey = _clean(re.sub(r"[\\d.]+", " ", jtxt))
        m = re.search(r"(\\d{2}(?:\\.\\d)?)\\s*$", jtxt)
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
            m = re.search(r"(\\d{2}(?:\\.\\d)?)\\s*$", jtxt)
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
            t = re.sub(r"^(栗東|美浦|地方|外国)\\s*[・･]\\s*", "", _clean(el.get_text(" ", strip=True)))
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
    m = re.search(r"(\\d{3})\\s*(?:[（(]\\s*([+\\-]?\\d+)\\s*[）)])?", wtxt)
    if m:
        try:
            bw = int(m.group(1))
            chg = int(m.group(2)) if m.group(2) is not None else None
        except Exception:
            bw = None; chg = None

    odds = None; pop = None
    o = tr.find("span", id=re.compile(r"^odds-1_"))
    if o is not None:
        m = re.search(r"\\d+(?:\\.\\d+)?", _clean(o.get_text(" ", strip=True)))
        if m:
            try: odds = float(m.group())
            except Exception: odds = None
    p = tr.find("span", id=re.compile(r"^ninki-1_"))
    if p is not None:
        m = re.search(r"\\d+", _clean(p.get_text(" ", strip=True)))
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


'''


def rep(old: str, new: str, label: str) -> None:
    global text
    assert old in text, f"NOT FOUND: {label}"
    assert text.count(old) == 1, f"NOT UNIQUE ({text.count(old)}): {label}"
    text = text.replace(old, new, 1)
    print("  ok:", label)


print("applying netkeiba parser fix")

# 1) ヘルパー挿入
anchor = '''    return {"date":date,"track":track,"title":title,"distance":distance,"surface":"障害" if surface.startswith("障") else ("芝" if surface.startswith("芝") else "ダート"),"condition":cond,"weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":corners,"carriedWeight":cw,"source":"netkeiba"}'''
rep(anchor, anchor + "\n" + HELPER, "insert _nk_row_horse helper")

# 2) _parse_recent_cell の斤量誤取得を修正
old_cw = '''    cw=0.0;mw=re.search(r"\\s(\\d{2}(?:\\.\\d)?)\\s",s)'''
new_cw = '''    # 斤量は「通過順」の直前にある。単純に最初の2桁を拾うと着順(10〜18)や
    # 頭数を誤って斤量にしてしまうため、通過順の直前を優先して探す。
    cw=0.0;mw=re.search(r"(?<!\\d)(\\d{2}(?:\\.\\d)?)\\s+(?=\\d{1,2}(?:-\\d{1,2}){1,3}(?!\\d))",s)
    if not mw:mw=re.search(r"(?<!\\d)(5[0-9](?:\\.\\d)?)(?!\\d)",s)
    if not mw:mw=re.search(r"\\s(\\d{2}(?:\\.\\d)?)\\s",s)'''
rep(old_cw, new_cw, "fix _parse_recent_cell carriedWeight")

# 3) _netkeiba_detail_rows 出走表ループ
old_block = '''            um=tr.find("td",class_=re.compile(r"^Umaban"));hi=tr.select_one("td.HorseInfo");name_a=hi.select_one(".HorseName a") if hi else None
            try:no=int(re.search(r"\\d+",_clean(um.get_text(" ",strip=True))).group()) if um else 0
            except Exception:no=0
            name=_clean(name_a.get_text(" ",strip=True)) if name_a else (_clean(hi.get_text(" ",strip=True)) if hi else "")
            if not no and not name:continue
            barei=_clean((tr.select_one("td.Barei") or {}).get_text(" ",strip=True) if tr.select_one("td.Barei") else "");sex=barei[:1] if barei else "";ma=re.search(r"(\\d+)",barei);age=int(ma.group(1)) if ma else 0
            jockey=_clean(tr.select_one("td.Jockey").get_text(" ",strip=True)) if tr.select_one("td.Jockey") else "";trainer=_clean(tr.select_one("td.Trainer").get_text(" ",strip=True)) if tr.select_one("td.Trainer") else ""
            tds=tr.find_all("td");cw=0.0
            if tr.select_one("td.Barei"):
                bidx=tds.index(tr.select_one("td.Barei"))
                if bidx+1<len(tds):
                    mm=re.search(r"\\d+(?:\\.\\d+)?",_clean(tds[bidx+1].get_text(" ",strip=True)));cw=float(mm.group()) if mm else 0.0
            wt=_clean(tr.select_one("td.Weight").get_text(" ",strip=True)) if tr.select_one("td.Weight") else "";bm=re.search(r"(\\d{3})(?:\\s*[（(]\\s*([+\\-]?\\d+)\\s*[）)])?",wt);bw=int(bm.group(1)) if bm else None;chg=int(bm.group(2)) if bm and bm.group(2) is not None else None
            odds=None;pop=None;odds_span=tr.find("span",id=re.compile(r"^odds-1_"));pop_span=tr.find("span",id=re.compile(r"^ninki-1_"));mo=re.search(r"\\d+(?:\\.\\d+)?",_clean(odds_span.get_text(" ",strip=True))) if odds_span else None;mp=re.search(r"\\d+",_clean(pop_span.get_text(" ",strip=True))) if pop_span else None
            if mo:
                try:odds=float(mo.group())
                except Exception:pass
            if mp:pop=int(mp.group())
            scratch_status=_scratch_status(_clean(tr.get_text(" ",strip=True)))
            rows[no or name]={"horseNumber":no,"name":name,"sex":sex,"age":age,"carriedWeight":cw,"jockey":jockey,"trainer":trainer,"bodyWeight":bw,"bodyWeightChange":chg,"winOdds":odds,"popularity":pop,"status":scratch_status,"scratched":bool(scratch_status),"recentRaces":[],"source":"netkeiba"}'''
new_block = '''            horse=_nk_row_horse(tr)
            if not horse:continue
            rows[horse["horseNumber"]]=horse'''
rep(old_block, new_block, "_netkeiba_detail_rows 出走表ループ")

# 4) _netkeiba_detail_rows 過去走ループ
old_past = '''            um=tr.find("td",class_=re.compile(r"^Umaban"));hi=tr.select_one("td.HorseInfo");name_a=hi.select_one(".HorseName a") if hi else None
            try:no=int(re.search(r"\\d+",_clean(um.get_text(" ",strip=True))).group()) if um else 0
            except Exception:no=0
            name=_clean(name_a.get_text(" ",strip=True)) if name_a else (_clean(hi.get_text(" ",strip=True)) if hi else "")
            key=no or name
            if key not in rows:rows[key]={"horseNumber":no,"name":name,"recentRaces":[],"source":"netkeiba"}
            rr=[]'''
new_past = '''            horse=_nk_row_horse(tr)
            if not horse:continue
            key=horse["horseNumber"]
            if key not in rows:rows[key]=horse
            rr=[]'''
rep(old_past, new_past, "_netkeiba_detail_rows 過去走ループ")

# 5) _netkeiba_past_rows_fast
old_fast = '''        um=tr.find("td",class_=re.compile(r"^Umaban"))
        hi=tr.select_one("td.HorseInfo")
        name_a=hi.select_one(".HorseName a") if hi else None
        try:no=int(re.search(r"\\d+",_clean(um.get_text(" ",strip=True))).group()) if um else 0
        except Exception:no=0
        name=_clean(name_a.get_text(" ",strip=True)) if name_a else (_clean(hi.get_text(" ",strip=True)) if hi else "")
        runs=[]
        for td in tr.find_all("td"):
            z=_parse_recent_cell(td.get_text(" ",strip=True))
            if z:runs.append(z)
            if len(runs)>=5:break
        if no or name:out.append({"horseNumber":no,"name":name,"recentRaces":runs[:5]})'''
new_fast = '''        horse=_nk_row_horse(tr)
        if not horse:continue
        runs=[]
        for td in tr.find_all("td"):
            z=_parse_recent_cell(td.get_text(" ",strip=True))
            if z:runs.append(z)
            if len(runs)>=5:break
        horse["recentRaces"]=runs[:5]
        out.append(horse)'''
rep(old_fast, new_fast, "_netkeiba_past_rows_fast ループ")

# 6) _netkeiba_fast_card_rows（中央 高速出走表）
old_card = '''        um=tr.find("td",class_=re.compile(r"^Umaban"))
        hi=tr.select_one("td.HorseInfo");name_a=hi.select_one(".HorseName a") if hi else None
        try:no=int(re.search(r"\\d+",_clean(um.get_text(" ",strip=True))).group()) if um else 0
        except Exception:no=0
        name=_clean(name_a.get_text(" ",strip=True)) if name_a else (_clean(hi.get_text(" ",strip=True)) if hi else "")
        if not no or not name:continue
        barei=_clean(tr.select_one("td.Barei").get_text(" ",strip=True)) if tr.select_one("td.Barei") else ""
        sex=barei[:1] if barei else "";ma=re.search(r"(\\d+)",barei);age=int(ma.group(1)) if ma else 0
        jockey=_clean(tr.select_one("td.Jockey").get_text(" ",strip=True)) if tr.select_one("td.Jockey") else ""
        trainer=_clean(tr.select_one("td.Trainer").get_text(" ",strip=True)) if tr.select_one("td.Trainer") else ""
        tds=tr.find_all("td");cw=0.0
        b=tr.select_one("td.Barei")
        if b and b in tds:
            bi=tds.index(b)
            if bi+1<len(tds):
                mm=re.search(r"\\d+(?:\\.\\d+)?",_clean(tds[bi+1].get_text(" ",strip=True)))
                cw=float(mm.group()) if mm else 0.0
        wt=_clean(tr.select_one("td.Weight").get_text(" ",strip=True)) if tr.select_one("td.Weight") else ""
        bm=re.search(r"(\\d{3})(?:\\s*[（(]\\s*([+\\-]?\\d+)\\s*[）)])?",wt)
        osel=tr.find("span",id=re.compile(r"^odds-1_"))
        psel=tr.find("span",id=re.compile(r"^ninki-1_"))
        mo=re.search(r"\\d+(?:\\.\\d+)?",_clean(osel.get_text(" ",strip=True))) if osel else None
        mp=re.search(r"\\d+",_clean(psel.get_text(" ",strip=True))) if psel else None
        odd=float(mo.group()) if mo else None
        pop=int(mp.group()) if mp else None
        rows.append({
            "horseNumber":no,"frameNumber":int((no+1)//2),"name":name,"sex":sex,"age":age,
            "carriedWeight":cw,"jockey":jockey,"trainer":trainer,
            "bodyWeight":int(bm.group(1)) if bm else None,
            "bodyWeightChange":int(bm.group(2)) if bm and bm.group(2) is not None else None,
            "winOdds":odd,"popularity":pop,
            "status":_scratch_status(_clean(tr.get_text(" ",strip=True))),
            "scratched":bool(_scratch_status(_clean(tr.get_text(" ",strip=True)))),
            "recentRaces":[],"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{},
            "source":"netkeiba高速出走表",
        })'''
new_card = '''        horse=_nk_row_horse(tr)
        if not horse:continue
        horse["source"]="netkeiba高速出走表"
        rows.append(horse)'''
rep(old_card, new_card, "_netkeiba_fast_card_rows ループ")

SRC.write_text(text, encoding="utf-8")
print(f"patched app.py: {before} -> {len(text)} chars")
