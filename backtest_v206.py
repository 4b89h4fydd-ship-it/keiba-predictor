#!/usr/bin/env python3
"""ARVEXQ v206: fast, leakage-guarded historical backtest + model search.

The script reads finalized race snapshots from the public ARVEXQ Cloudflare/D1 day API.
Only explicitly whitelisted *pre-race* horse fields are used as model inputs. The
race result/payout is read only after scoring, as the evaluation label.

No third-party packages are required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

JST = timezone(timedelta(hours=9))
MODEL_VERSION = "arvexq-backtest-2026.10-v206"
SEED = 206

FEATURES = [
    "p1_saved",
    "eval_score",
    "race_perf",
    "representative",
    "distance",
    "track",
    "going",
    "level",
    "lap",
    "jockey",
    "trainer",
    "body",
    "condition_change",
    "early3",
    "ten",
    "late_role",
    "evidence",
]

# A conservative starting point close to the current market-blind P1 philosophy.
BASE_WEIGHTS = {
    "p1_saved": 0.29,
    "eval_score": 0.13,
    "race_perf": 0.13,
    "representative": 0.09,
    "distance": 0.07,
    "track": 0.065,
    "going": 0.035,
    "level": 0.055,
    "lap": 0.025,
    "jockey": 0.025,
    "trainer": 0.015,
    "body": 0.010,
    "condition_change": 0.015,
    "early3": 0.025,
    "ten": 0.020,
    "late_role": 0.025,
    "evidence": 0.025,
}

FORBIDDEN_MODEL_FIELDS = {
    "result", "finishers", "payouts", "actualFlow", "actualOrder", "finish",
    "finishPosition", "resultTime", "winOdds", "popularity", "marketProbability",
    "raceStatus", "payoutSource", "payoutError",
}


def clamp(v: Any, lo: float = 0.0, hi: float = 1.0, default: float = 0.5) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return lo if x < lo else hi if x > hi else x
    except (TypeError, ValueError):
        return default


def num(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def intval(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def nested(d: dict, *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return default if cur is None else cur


def norm01(v: Any, default: float = 0.5) -> float:
    x = num(v, float("nan"))
    if not math.isfinite(x):
        return default
    if x > 1.5:  # stored role/eval scores often use 0..100
        x /= 100.0
    return clamp(x, 0.0, 1.0, default)


def is_scratched(h: dict) -> bool:
    if h.get("scratched") is True:
        return True
    s = str(h.get("status") or "")
    return bool(re.search(r"取消|除外|競走除外|出走取消", s))


def winner_order(detail: dict) -> list[int]:
    rows = ((detail.get("result") or {}).get("finishers") or [])
    clean = []
    for z in rows:
        f = intval(z.get("finish"), 0)
        no = intval(z.get("horseNumber"), 0)
        if f > 0 and no > 0:
            clean.append((f, no))
    clean.sort()
    return [no for _, no in clean]


def payout_rows(detail: dict) -> list[dict]:
    return list(((detail.get("result") or {}).get("payouts") or []))


def component(e: dict, *names: str, default: float = 0.5) -> float:
    c = e.get("components") or {}
    for name in names:
        if name in c and c.get(name) is not None:
            return norm01(c.get(name), default)
    return default


def feature_vector(h: dict) -> dict[str, float]:
    """Whitelisted pre-race feature extraction only."""
    e = h.get("integratedEvaluation") or {}
    pm = h.get("precomputedMetrics") or {}
    fit = pm.get("fit") or {}
    st = pm.get("style") or {}
    samples = max(intval(st.get("samples"), 0), intval(e.get("samples"), 0))
    fullness = clamp(num(e.get("dataCompleteness"), 50.0) / 100.0, 0, 1, .5)
    evidence = clamp(0.55 * min(1.0, samples / 5.0) + 0.45 * fullness, 0, 1, .5)
    late_role = clamp(
        0.42 * norm01(st.get("moved3"), .0)
        + 0.32 * norm01(st.get("mid"), .0)
        + 0.26 * norm01(st.get("close"), .0),
        0, 1, .0,
    )
    return {
        "p1_saved": norm01(e.get("p1Score"), norm01(e.get("score"), .5)),
        "eval_score": norm01(e.get("score"), .5),
        "race_perf": component(e, "racePerformance", default=.5),
        "representative": component(e, "representative", default=.5),
        "distance": component(e, "distanceFit", default=norm01(fit.get("distance"), .5)),
        "track": component(e, "courseFit", default=norm01(fit.get("track"), .5)),
        "going": component(e, "goingFit", default=norm01(fit.get("condition"), .5)),
        "level": component(e, "opponentLevelScore", default=norm01(fit.get("level"), .5)),
        "lap": component(e, "lapScore", default=.5),
        "jockey": component(e, "jockeyScore", "jockeyResults", default=.5),
        "trainer": component(e, "trainerScore", "trainerResults", default=.5),
        "body": component(e, "bodyWeightScore", default=.5),
        "condition_change": component(e, "conditionChangeScore", default=.5),
        "early3": norm01(st.get("early3"), .0),
        "ten": norm01(st.get("ten"), .5),
        "late_role": late_role,
        "evidence": evidence,
    }


def saved_role(h: dict, role: str) -> float:
    e = h.get("integratedEvaluation") or {}
    return norm01(e.get({"p1": "p1Score", "p2": "p2Score", "p3": "p3Score"}[role]), .5)


@dataclass
class HorseRow:
    no: int
    features: dict[str, float]
    p1: float
    p2: float
    p3: float


@dataclass
class RaceRow:
    race_id: str
    race_date: str
    circuit: str
    track: str
    race_no: int
    surface: str
    distance: int
    field: int
    horses: list[HorseRow]
    order: list[int]
    payouts: list[dict]

    @property
    def winner(self) -> int:
        return self.order[0] if self.order else 0


def race_from_detail(d: dict) -> RaceRow | None:
    order = winner_order(d)
    if len(order) < 3:
        return None
    horses = []
    for h in d.get("horses") or []:
        no = intval(h.get("horseNumber"), 0)
        if no <= 0 or is_scratched(h):
            continue
        e = h.get("integratedEvaluation") or {}
        if not e:
            continue
        horses.append(HorseRow(no, feature_vector(h), saved_role(h, "p1"), saved_role(h, "p2"), saved_role(h, "p3")))
    if len(horses) < 4 or order[0] not in {h.no for h in horses}:
        return None
    return RaceRow(
        race_id=str(d.get("id") or ""), race_date=str(d.get("date") or ""),
        circuit=str(d.get("circuit") or ""), track=str(d.get("track") or ""),
        race_no=intval(d.get("raceNumber"), 0), surface=str(d.get("surface") or ""),
        distance=intval(d.get("distance"), 0), field=len(horses), horses=horses,
        order=order, payouts=payout_rows(d),
    )


def api_json(url: str, timeout: int = 20, retries: int = 3) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-v206-backtest/1.0", "accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"API fetch failed: {url}: {last}")


def collect_api(api_url: str, days: int, outdir: Path) -> tuple[list[RaceRow], list[dict]]:
    rawdir = outdir / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(JST).date()
    races: list[RaceRow] = []
    daily: list[dict] = []
    for offset in range(1, days + 1):
        d = today - timedelta(days=offset)
        ds = d.isoformat()
        url = api_url.rstrip("/") + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        try:
            payload = api_json(url)
            (rawdir / f"{ds}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            added = 0
            for detail in payload.get("details") or []:
                rr = race_from_detail(detail)
                if rr:
                    races.append(rr); added += 1
            daily.append({"date": ds, "apiRaceCount": intval(payload.get("raceCount")), "apiDetailCount": intval(payload.get("detailCount")), "usableFinalRaces": added, "error": ""})
            print(f"{ds}: API {payload.get('raceCount', 0)} races / usable final {added}")
        except Exception as exc:
            daily.append({"date": ds, "apiRaceCount": 0, "apiDetailCount": 0, "usableFinalRaces": 0, "error": str(exc)[:200]})
            print(f"{ds}: ERROR {exc}", file=sys.stderr)
    races.sort(key=lambda r: (r.race_date, r.circuit, r.track, r.race_no, r.race_id))
    return races, daily


def collect_files(paths: list[str]) -> list[RaceRow]:
    races: list[RaceRow] = []
    for pstr in paths:
        p = Path(pstr)
        files = list(p.glob("*.json")) if p.is_dir() else [p]
        for f in files:
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            details = payload.get("details") if isinstance(payload, dict) else payload
            for d in details or []:
                rr = race_from_detail(d)
                if rr:
                    races.append(rr)
    races.sort(key=lambda r: (r.race_date, r.circuit, r.track, r.race_no, r.race_id))
    return races


def normalized_weights(w: dict[str, float]) -> dict[str, float]:
    z = {k: max(0.0001, float(w.get(k, 0))) for k in FEATURES}
    s = sum(z.values())
    return {k: v / s for k, v in z.items()}


def score_horse(h: HorseRow, w: dict[str, float]) -> float:
    return sum(w[k] * h.features[k] for k in FEATURES)


def race_rank(r: RaceRow, w: dict[str, float] | None = None, baseline: bool = False) -> list[int]:
    if baseline:
        return [h.no for h in sorted(r.horses, key=lambda h: (-h.p1, h.no))]
    assert w is not None
    return [h.no for h in sorted(r.horses, key=lambda h: (-score_horse(h, w), h.no))]


def metric_block(races: list[RaceRow], w: dict[str, float] | None = None, baseline: bool = False) -> dict:
    if not races:
        return {"races": 0, "top1": 0.0, "top3": 0.0, "top5": 0.0, "mrr": 0.0, "objective": 0.0}
    top1 = top3 = top5 = 0
    rr_sum = 0.0
    ranks = []
    for r in races:
        ranking = race_rank(r, w, baseline)
        try: rank = ranking.index(r.winner) + 1
        except ValueError: rank = 999
        ranks.append(rank)
        top1 += rank == 1
        top3 += rank <= 3
        top5 += rank <= 5
        rr_sum += 1.0 / rank if rank < 999 else 0
    n = len(races)
    a, b, c, m = top1/n, top3/n, top5/n, rr_sum/n
    objective = a*.62 + b*.20 + m*.14 + c*.04
    return {"races": n, "top1": a, "top3": b, "top5": c, "mrr": m, "objective": objective,
            "medianWinnerRank": statistics.median(ranks) if ranks else None}


def random_candidate(base: dict[str, float], rnd: random.Random, scale: float = 0.48) -> dict[str, float]:
    # Log-normal perturbation keeps every weight positive while exploring broad alternatives.
    out = {}
    for k in FEATURES:
        b = max(0.001, base[k])
        out[k] = b * math.exp(rnd.gauss(0, scale))
    return normalized_weights(out)


def mutate_candidate(parent: dict[str, float], rnd: random.Random, scale: float = 0.20) -> dict[str, float]:
    return normalized_weights({k: max(0.0001, parent[k] * math.exp(rnd.gauss(0, scale))) for k in FEATURES})


def split_time(races: list[RaceRow]) -> tuple[list[RaceRow], list[RaceRow], list[RaceRow]]:
    n = len(races)
    if n < 15:
        return races, [], []
    a = max(5, int(n * .60)); b = max(a + 3, int(n * .80))
    b = min(b, n - 3)
    return races[:a], races[a:b], races[b:]


def optimize(races: list[RaceRow], iterations: int, seed: int) -> tuple[dict[str, float], dict]:
    train, valid, holdout = split_time(races)
    base = normalized_weights(BASE_WEIGHTS)
    if len(train) < 10 or not valid:
        return base, {"searched": False, "reason": "insufficient chronological sample", "train": len(train), "validation": len(valid), "holdout": len(holdout)}
    rnd = random.Random(seed)
    candidates: list[tuple[float, dict[str, float]]] = []
    base_m = metric_block(train, base)
    candidates.append((base_m["objective"], base))
    # Broad search.
    for _ in range(max(1, int(iterations * .72))):
        w = random_candidate(base, rnd)
        m = metric_block(train, w)
        candidates.append((m["objective"], w))
    candidates.sort(key=lambda z: z[0], reverse=True)
    parents = [w for _, w in candidates[:12]]
    # Local refinement around the strongest train candidates.
    for _ in range(max(1, iterations - len(candidates))):
        w = mutate_candidate(rnd.choice(parents), rnd)
        m = metric_block(train, w)
        candidates.append((m["objective"], w))
    candidates.sort(key=lambda z: z[0], reverse=True)
    shortlist = candidates[:40]
    selected = None
    selected_score = -1e9
    for train_obj, w in shortlist:
        vm = metric_block(valid, w)
        # Generalization penalty: do not reward train-only spikes.
        gap = max(0.0, train_obj - vm["objective"])
        score = vm["objective"] - gap * .18
        if score > selected_score:
            selected_score = score; selected = w
    assert selected is not None
    return selected, {
        "searched": True, "iterations": iterations,
        "train": len(train), "validation": len(valid), "holdout": len(holdout),
        "baselineTrain": metric_block(train, base), "candidateTrain": metric_block(train, selected),
        "baselineValidation": metric_block(valid, base), "candidateValidation": metric_block(valid, selected),
        "baselineHoldout": metric_block(holdout, base, baseline=True),
        "storedP1Holdout": metric_block(holdout, baseline=True),
        "candidateHoldout": metric_block(holdout, selected),
    }


def softmax(values: list[float], temp: float = .10) -> list[float]:
    if not values: return []
    mx = max(values); ex = [math.exp((v-mx)/max(.035,temp)) for v in values]; s = sum(ex) or 1
    return [v/s for v in ex]


def combo_key(combo: Iterable[int], ordered: bool) -> tuple[int, ...]:
    z = tuple(int(x) for x in combo)
    return z if ordered else tuple(sorted(z))


def ticket_policy(r: RaceRow, w: dict[str, float] | None, baseline: bool) -> list[dict]:
    hs = r.horses
    if baseline:
        p1 = softmax([h.p1 for h in hs], .095)
    else:
        p1 = softmax([score_horse(h, w or normalized_weights(BASE_WEIGHTS)) for h in hs], .095)
    p2 = softmax([h.p2 for h in hs], .105)
    p3 = softmax([h.p3 for h in hs], .115)
    nos = [h.no for h in hs]
    # Ordered probabilities.
    exact = []
    tri = []
    for i,a in enumerate(nos):
        for j,b in enumerate(nos):
            if i == j: continue
            exact.append((p1[i]*p2[j], (a,b)))
            for k,c in enumerate(nos):
                if k == i or k == j: continue
                tri.append((p1[i]*p2[j]*p3[k], (a,b,c)))
    exact.sort(reverse=True); tri.sort(reverse=True)
    qmap: dict[tuple[int,int], float] = defaultdict(float)
    tmap: dict[tuple[int,int,int], float] = defaultdict(float)
    for s,c in exact: qmap[combo_key(c,False)] += s
    for s,c in tri: tmap[combo_key(c,False)] += s
    quin = sorted(((s,c) for c,s in qmap.items()), reverse=True)
    trio = sorted(((s,c) for c,s in tmap.items()), reverse=True)
    wmap: dict[tuple[int,int], float] = defaultdict(float)
    for s,c in trio:
        a,b,c3 = c
        wmap[combo_key((a,b),False)] += s
        wmap[combo_key((a,c3),False)] += s
        wmap[combo_key((b,c3),False)] += s
    wide = sorted(((s,c) for c,s in wmap.items()), reverse=True)
    field = len(nos)
    base_wide = 6/(field*(field-1)) if field>1 else 0
    base_q = 2/(field*(field-1)) if field>1 else 0
    base_trio = 6/(field*(field-1)*(field-2)) if field>2 else 0
    base_tri = 1/(field*(field-1)*(field-2)) if field>2 else 0
    items=[]
    def top(list_, n, threshold): return [tuple(c) for s,c in list_[:n] if s >= threshold]
    if wide and wide[0][0] >= base_wide*1.22:
        c = top(wide, 2 if wide[0][0]>=base_wide*2 else 3, max(base_wide*1.10, wide[0][0]*.76))
        if c: items.append({"level":"本線","kind":"ワイド","combos":c})
    if trio and trio[0][0] >= base_trio*1.30:
        c=top(trio,4,max(base_trio*1.05,trio[0][0]*.62))
        if c: items.append({"level":"押さえ","kind":"3連複","combos":c})
    if quin and quin[0][0] >= base_q*1.45:
        p1_sorted=sorted(p1,reverse=True); p1_clear=(p1_sorted[0]-p1_sorted[1]) if len(p1_sorted)>1 else 0
        ordered_ratio=exact[0][0]/max(1e-12,exact[1][0]) if len(exact)>1 else 9
        if p1_clear >= max(.020,1/field*.16) and ordered_ratio>=1.45:
            c=top(exact,2,max((exact[0][0] if exact else 0)*.70,base_q*.32))
            if c: items.append({"level":"強気","kind":"馬単","combos":c})
        else:
            c=top(quin,2,max(base_q*1.10,quin[0][0]*.76))
            if c: items.append({"level":"強気","kind":"馬連","combos":c})
    if tri:
        p1_sorted=sorted(p1,reverse=True); clear=(p1_sorted[0]-p1_sorted[1]) if len(p1_sorted)>1 else 0
        ratio=tri[0][0]/max(1e-12,tri[1][0]) if len(tri)>1 else 9
        if clear >= max(.018,1/field*.14) and ratio>=1.18 and tri[0][0]>=base_tri*2.20:
            c=top(tri,4,max(base_tri*1.25,tri[0][0]*.56))
            if c: items.append({"level":"3連単チャレンジ","kind":"3連単","combos":c})
    return items


def ticket_hit(kind: str, combo: tuple[int,...], order: list[int]) -> bool:
    if len(order)<3: return False
    t=order[:3]
    if kind=="ワイド": return combo[0] in t and combo[1] in t
    if kind=="馬連": return set(combo)==set(t[:2])
    if kind=="馬単": return tuple(combo)==tuple(t[:2])
    if kind=="3連複": return set(combo)==set(t[:3])
    if kind=="3連単": return tuple(combo)==tuple(t[:3])
    if kind=="単勝": return combo[0]==t[0]
    return False


def parse_payout_combo(text: str) -> tuple[int,...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(text or "")))


def payout_return(kind: str, combos: list[tuple[int,...]], payouts: list[dict]) -> int | None:
    if not payouts: return None
    total=0; seen_type=False
    ordered=kind in {"馬単","3連単"}
    wanted={combo_key(c,ordered) for c in combos}
    for row in payouts:
        if str(row.get("type") or "") != kind: continue
        seen_type=True
        c=parse_payout_combo(str(row.get("combination") or ""))
        if not c: continue
        if combo_key(c,ordered) in wanted:
            total += intval(row.get("amount"),0)
    return total if seen_type else None


def ticket_metrics(races: list[RaceRow], w: dict[str,float] | None, baseline: bool) -> dict:
    stats=defaultdict(lambda:{"issued":0,"hit":0,"points":0,"stake":0,"return":0,"roiRaces":0,"roiStake":0})
    for r in races:
        items=ticket_policy(r,w,baseline)
        for item in items:
            kind=item["kind"]; combos=item["combos"]; s=stats[kind]
            s["issued"]+=1;s["points"]+=len(combos);s["stake"]+=100*len(combos)
            if any(ticket_hit(kind,c,r.order) for c in combos):s["hit"]+=1
            ret=payout_return(kind,combos,r.payouts)
            if ret is not None:
                s["return"]+=ret;s["roiRaces"]+=1;s["roiStake"]+=100*len(combos)
    out={}
    for kind,s in stats.items():
        out[kind]={**s,
            "hitRate": s["hit"]/s["issued"] if s["issued"] else 0,
            "avgPoints": s["points"]/s["issued"] if s["issued"] else 0,
            "roi": s["return"]/s["roiStake"] if s["roiStake"] else None,
        }
    return out


def segment_name(r: RaceRow) -> list[str]:
    seg=["ALL", f"circuit:{r.circuit or '不明'}"]
    if r.track: seg.append(f"track:{r.track}")
    if r.surface: seg.append(f"surface:{r.surface}")
    d=r.distance
    bucket="<=1400" if d<=1400 else "1500-1800" if d<=1800 else "1900-2200" if d<=2200 else ">=2300"
    seg.append(f"distance:{bucket}")
    return seg


def segment_report(races: list[RaceRow], candidate: dict[str,float], min_n: int=12) -> list[dict]:
    groups=defaultdict(list)
    for r in races:
        for k in segment_name(r): groups[k].append(r)
    rows=[]
    for k,rs in groups.items():
        if len(rs)<min_n and k!="ALL":continue
        b=metric_block(rs,baseline=True);c=metric_block(rs,candidate)
        rows.append({"segment":k,"races":len(rs),"baselineTop1":b["top1"],"candidateTop1":c["top1"],"deltaTop1":c["top1"]-b["top1"],"baselineTop3":b["top3"],"candidateTop3":c["top3"],"deltaTop3":c["top3"]-b["top3"],"baselineMRR":b["mrr"],"candidateMRR":c["mrr"]})
    rows.sort(key=lambda x:(0 if x["segment"]=="ALL" else 1,-x["races"],x["segment"]))
    return rows


def promotion_decision(holdout: list[RaceRow], candidate: dict[str,float]) -> dict:
    if len(holdout)<20:
        return {"promote":False,"reason":f"holdout不足 ({len(holdout)} races; 20以上必要)"}
    b=metric_block(holdout,baseline=True);c=metric_block(holdout,candidate)
    delta1=c["top1"]-b["top1"];delta3=c["top3"]-b["top3"]
    circuit_bad=False;details=[]
    for circuit in sorted({r.circuit for r in holdout}):
        rs=[r for r in holdout if r.circuit==circuit]
        if len(rs)<8:continue
        bb=metric_block(rs,baseline=True);cc=metric_block(rs,candidate)
        d=cc["top1"]-bb["top1"];details.append({"circuit":circuit,"races":len(rs),"deltaTop1":d})
        if d < -0.05:circuit_bad=True
    promote=(delta1>=0.025 and delta3>=-0.01 and not circuit_bad) or (delta1>=0.015 and c["mrr"]-b["mrr"]>=0.025 and delta3>=0 and not circuit_bad)
    reason=(f"holdout ◎相当1着率 {b['top1']:.1%}→{c['top1']:.1%} ({delta1:+.1%}), "
            f"勝ち馬Top3 {b['top3']:.1%}→{c['top3']:.1%} ({delta3:+.1%})")
    if circuit_bad:reason+="。一部circuitで悪化が大きいため自動採用禁止"
    elif not promote:reason+="。改善幅が採用基準未満"
    else:reason+="。採用候補基準を通過"
    return {"promote":promote,"reason":reason,"baseline":b,"candidate":c,"circuits":details}


def fmt_pct(x: Any) -> str:
    try:return f"{float(x)*100:.1f}%"
    except Exception:return "—"


def write_report(outdir: Path, races: list[RaceRow], eval_races: list[RaceRow], daily: list[dict], candidate: dict[str,float], search: dict, segments: list[dict], tickets_base: dict, tickets_candidate: dict, promo: dict, circuit_models: dict) -> None:
    base_all=metric_block(eval_races,baseline=True);cand_all=metric_block(eval_races,candidate)
    report={
        "version":MODEL_VERSION,"generatedAt":datetime.now(JST).isoformat(),"raceCount":len(races),
        "leakageGuard":{"resultUsedAsFeature":False,"oddsUsedAsFeature":False,"forbiddenFields":sorted(FORBIDDEN_MODEL_FIELDS),"inputFeatureWhitelist":FEATURES},
        "baseline":base_all,"candidate":cand_all,"search":search,"candidateWeights":candidate,
        "promotion":promo,"segments":segments,"tickets":{"baseline":tickets_base,"candidate":tickets_candidate},"daily":daily,"evaluationRaceCount":len(eval_races),"circuitCandidates":circuit_models,
    }
    (outdir/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (outdir/"candidate_model_v206.json").write_text(json.dumps({"version":MODEL_VERSION,"weights":candidate,"promotion":promo,"circuitCandidates":circuit_models},ensure_ascii=False,indent=2),encoding="utf-8")

    with (outdir/"segments.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=["segment","races","baselineTop1","candidateTop1","deltaTop1","baselineTop3","candidateTop3","deltaTop3","baselineMRR","candidateMRR"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(segments)

    # Per-race audit lets us inspect exactly where candidate differs from baseline.
    with (outdir/"race_audit.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=["date","circuit","track","raceNo","raceId","winner","baselinePick","candidatePick","baselineWinnerRank","candidateWinnerRank"]
        wri=csv.DictWriter(f,fieldnames=fields);wri.writeheader()
        for r in races:
            br=race_rank(r,baseline=True);cr=race_rank(r,candidate)
            wri.writerow({"date":r.race_date,"circuit":r.circuit,"track":r.track,"raceNo":r.race_no,"raceId":r.race_id,"winner":r.winner,"baselinePick":br[0] if br else "","candidatePick":cr[0] if cr else "","baselineWinnerRank":br.index(r.winner)+1 if r.winner in br else 999,"candidateWinnerRank":cr.index(r.winner)+1 if r.winner in cr else 999})

    lines=[]
    lines.append("# ARVEXQ v206 高速バックテスト")
    lines.append("")
    lines.append(f"- 取得済み対象: **{len(races)}レース** / 最終評価(Holdout): **{len(eval_races)}レース**")
    lines.append("- 結果・払戻・オッズ・人気は**モデル入力に不使用**。結果は採点時だけ使用。")
    lines.append(f"- 判定: **{'採用候補' if promo.get('promote') else 'まだ採用しない'}** — {promo.get('reason','')}")
    lines.append("")
    lines.append("## 勝ち馬順位")
    lines.append("")
    lines.append("| 指標 | 現行保存P1 | v206候補 | 差 |")
    lines.append("|---|---:|---:|---:|")
    for key,label in [("top1","◎相当1着率"),("top3","勝ち馬Top3"),("top5","勝ち馬Top5"),("mrr","平均逆順位(MRR)")]:
        b=base_all[key];c=cand_all[key]
        if key=="mrr": lines.append(f"| {label} | {b:.3f} | {c:.3f} | {c-b:+.3f} |")
        else: lines.append(f"| {label} | {fmt_pct(b)} | {fmt_pct(c)} | {fmt_pct(c-b)} |")
    lines.append("")
    lines.append("## 券種別（100円/点でシミュレーション）")
    lines.append("")
    lines.append("| 券種 | 現行Hit | v206 Hit | 現行平均点数 | v206平均点数 | v206 ROI* |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    kinds=sorted(set(tickets_base)|set(tickets_candidate),key=lambda x:["ワイド","馬連","馬単","3連複","3連単"].index(x) if x in ["ワイド","馬連","馬単","3連複","3連単"] else 99)
    for k in kinds:
        b=tickets_base.get(k,{}) ; c=tickets_candidate.get(k,{})
        roi=c.get("roi")
        lines.append(f"| {k} | {fmt_pct(b.get('hitRate',0))} ({b.get('issued',0)}) | {fmt_pct(c.get('hitRate',0))} ({c.get('issued',0)}) | {b.get('avgPoints',0):.2f} | {c.get('avgPoints',0):.2f} | {'—' if roi is None else fmt_pct(roi)} |")
    lines.append("")
    lines.append("* ROIは払戻データが保存されているレースだけで計算。Hit率とは分母が異なる場合があります。")
    lines.append("")
    lines.append("## 主なセグメント")
    lines.append("")
    lines.append("| セグメント | R | 現行Top1 | v206Top1 | 差 | 現行Top3 | v206Top3 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for z in segments[:24]:
        lines.append(f"| {z['segment']} | {z['races']} | {fmt_pct(z['baselineTop1'])} | {fmt_pct(z['candidateTop1'])} | {fmt_pct(z['deltaTop1'])} | {fmt_pct(z['baselineTop3'])} | {fmt_pct(z['candidateTop3'])} |")
    lines.append("")
    if circuit_models:
        lines.append("## 中央 / 地方 別候補")
        lines.append("")
        lines.append("| 区分 | R | 採用候補 | Holdout Top1差 | 理由 |")
        lines.append("|---|---:|---|---:|---|")
        for ck,cv in sorted(circuit_models.items()):
            pd=cv.get("promotion") or {}; bb=(pd.get("baseline") or {}).get("top1",0); cc=(pd.get("candidate") or {}).get("top1",0)
            lines.append(f"| {ck} | {cv.get('races',0)} | {'YES' if pd.get('promote') else 'NO'} | {fmt_pct(cc-bb)} | {pd.get('reason','')} |")
        lines.append("")
    lines.append("## 採用ルール")
    lines.append("")
    lines.append("過去全件に合わせて採用するのではなく、時系列で Train → Validation → Holdout に分割。**Holdoutを改善し、Top3を壊さず、中央/地方のどちらかだけ大崩れしない場合だけ採用候補**にします。")
    lines.append("")
    lines.append("`candidate_model_v206.json` が次の本番エンジン候補、`race_audit.csv` が1レース単位の差分確認用です。")
    (outdir/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def optimize_circuits(races: list[RaceRow], iterations: int, seed: int) -> dict:
    out={}
    for idx,circuit in enumerate(sorted({r.circuit for r in races if r.circuit})):
        rs=[r for r in races if r.circuit==circuit]
        if len(rs)<35:
            continue
        w,search=optimize(rs,max(300,iterations//2),seed+101*(idx+1))
        _,valid,hold=split_time(rs); evalset=hold if hold else valid
        out[circuit]={"races":len(rs),"weights":w,"search":search,"promotion":promotion_decision(evalset,w)}
    return out


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--api-url",default=os.getenv("ARVEXQ_API_URL","https://kraiz-api.4b89h4fydd.workers.dev"))
    ap.add_argument("--days",type=int,default=14)
    ap.add_argument("--iterations",type=int,default=1800)
    ap.add_argument("--out",default="backtest-v206")
    ap.add_argument("--input",action="append",default=[],help="Local JSON file/dir instead of API (repeatable)")
    ap.add_argument("--seed",type=int,default=SEED)
    args=ap.parse_args()
    outdir=Path(args.out);outdir.mkdir(parents=True,exist_ok=True)
    if args.input:
        races=collect_files(args.input);daily=[]
    else:
        races,daily=collect_api(args.api_url,max(1,min(args.days,120)),outdir)
    # Deduplicate by race id; newest/raw duplicate is irrelevant because each day endpoint is unique.
    uniq={r.race_id:r for r in races if r.race_id};races=sorted(uniq.values(),key=lambda r:(r.race_date,r.circuit,r.track,r.race_no,r.race_id))
    if len(races)<8:
        (outdir/"report.md").write_text(f"# ARVEXQ v206\n\n有効な確定レースが **{len(races)}件** しかありません。D1の履歴補完後に再実行してください。\n",encoding="utf-8")
        (outdir/"report.json").write_text(json.dumps({"version":MODEL_VERSION,"raceCount":len(races),"daily":daily,"error":"insufficient races"},ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"Only {len(races)} usable races; report created but optimization skipped")
        return 0
    candidate,search=optimize(races,max(100,args.iterations),args.seed)
    train,valid,holdout=split_time(races)
    eval_set=holdout if holdout else valid if valid else races
    promo=promotion_decision(eval_set,candidate)
    segments=segment_report(eval_set,candidate,min_n=max(8,min(20,len(eval_set)//5 if eval_set else 8)))
    tickets_base=ticket_metrics(eval_set,None,True);tickets_candidate=ticket_metrics(eval_set,candidate,False)
    circuit_models=optimize_circuits(races,max(300,args.iterations//2),args.seed)
    write_report(outdir,races,eval_set,daily,candidate,search,segments,tickets_base,tickets_candidate,promo,circuit_models)
    print(json.dumps({"races":len(races),"evalRaces":len(eval_set),"promotion":promo,"baseline":metric_block(eval_set,baseline=True),"candidate":metric_block(eval_set,candidate)},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
