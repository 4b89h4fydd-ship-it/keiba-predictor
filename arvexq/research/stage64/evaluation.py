"""Outcome-only scoring after prediction freeze, keeping the complete cohort."""
from collections import Counter
import math
import statistics
from arvexq.research.stage63.forward import digest
from .protocol import ARMS
from .circuits import active


def summarize(rows):
    total=len(rows)
    scored=[r for r in rows if r["scored"]]
    n=len(scored)
    returns=[r["returnYen"] for r in scored if r["returnYen"] is not None]
    payout_complete=len(returns)==n and n>0
    stake=sum(r["stakeYen"] for r in scored)
    returned=sum(returns) if payout_complete else None
    loss=[r["logloss"] for r in scored if r["logloss"] is not None]
    brier=[r["brier"] for r in scored if r["brier"] is not None]
    hits=sum(r["trifectaHit"] for r in scored)
    top1=sum(r["winnerTop1"] for r in scored)
    top3=sum(r["winnerTop3"] for r in scored)
    axis=sum(r["axisTop3Hit"] for r in scored)
    largest=sorted(scored,key=lambda r:r["returnYen"] or 0,reverse=True)[:2]
    reduced_stake=stake-sum(r["stakeYen"] for r in largest)
    reduced_return=returned-sum(r["returnYen"] for r in largest) if payout_complete else None
    return {"cohortRaces":total,"scoredRaces":n,"unscoredRaces":total-n,
            "scoredDates":len({r["date"] for r in scored}),
            "coverage":n/total if total else None,
            "winnerTop1Hits":top1,"winnerTop3Hits":top3,"axisTop3Hits":axis,
            "trifectaHits":hits,"trifectaHitRateScored":hits/n if n else None,
            "trifectaHitRateAllCohort":hits/total if total else None,
            "meanLogloss":statistics.mean(loss) if loss else None,
            "meanBrier":statistics.mean(brier) if brier else None,
            "probabilityMetricRaces":len(loss),"stakeYen":stake,
            "payoutCoveredScoredRaces":len(returns),"returnYen":returned,
            "roiPct":100*returned/stake if payout_complete and stake else None,
            "top2ReturnShare":sum(sorted(returns,reverse=True)[:2])/returned if returned else None,
            "roiWithoutTwoLargestReturnsPct":100*reduced_return/reduced_stake if payout_complete and reduced_stake else None,
            "concentrationDiagnosticOnly":True,
            "target80Observed":hits/n>=.8 if n else False,
            "target90Observed":hits/n>=.9 if n else False}


def evaluate(batch, results, *, independently_verified=False):
    # Never accepts this boolean from CLI JSON. Authenticated CLI owns this flag.
    receipts=batch["receipts"]
    ids=[r["snapshot"]["raceId"] for r in receipts]
    if len(set(ids))!=len(ids) or sorted(ids)!=batch["cohort"]:
        raise ValueError("frozen cohort mismatch")
    if len({r["raceId"] for r in results})!=len(results) or set(ids)!={r["raceId"] for r in results}:
        raise ValueError("results must match entire frozen cohort exactly")
    labels={r["raceId"]:r for r in results}
    rows=[]
    for receipt in receipts:
        snap=receipt["snapshot"]
        outcome=labels[snap["raceId"]]
        if outcome.get("circuit")!=snap["circuit"] or outcome.get("date")!=snap["input"]["date"] or outcome.get("status")!="confirmed":
            raise ValueError("unconfirmed or mismatched outcome identity")
        orders=outcome.get("orders")
        if not isinstance(orders,list) or not orders:
            raise ValueError("official podium orders missing")
        roster={h["horseNumber"] for h in snap["input"]["horses"] if active(h)}
        if any(not isinstance(o,list) or len(o)!=3 or len(set(o))!=3 or
               any(type(n) is not int or n not in roster for n in o) for o in orders):
            raise ValueError("outcome order outside frozen active roster")
        actuals={tuple(o) for o in orders}
        if len(actuals)!=len(orders):raise ValueError("duplicate official order")
        payouts=outcome.get("payouts")
        price={}
        if payouts is not None:
            if not isinstance(payouts,list):raise ValueError("invalid payouts")
            seen_prices=set()
            for p in payouts:
                combo=tuple(p["order"])
                amount=p["amount"]
                if combo not in actuals or combo in seen_prices:
                    raise ValueError("invalid/duplicate official trifecta payout")
                seen_prices.add(combo)
                if amount is None:
                    continue
                if type(amount) is not int or amount<=0:
                    raise ValueError("invalid official trifecta payout amount")
                price[combo]=amount
        winners={o[0] for o in orders}
        for arm in ARMS:
            p=snap["predictions"][arm]
            tickets=p["stages"]["tickets"]["value"]
            record={"raceId":snap["raceId"],"circuit":snap["circuit"],"date":snap["input"]["date"],
                    "arm":arm,"scored":tickets is not None,"winnerTop1":False,
                    "winnerTop3":False,"axisTop3Hit":False,"trifectaHit":False,
                    "logloss":None,"brier":None,"stakeYen":0,"returnYen":None}
            if tickets is not None:
                combos=[tuple(c) for c in tickets["hypotheticalTrifectaTop10"]]
                if len(combos)>10 or len(combos)!=len(set(combos)) or not combos:
                    raise ValueError("invalid frozen ticket selection")
                win={int(k):v for k,v in p["stages"]["probability"]["value"]["win"].items()}
                rank=sorted(win,key=lambda n:(-win[n],n))
                axis=p["stages"]["marks"]["value"]["axisRole"]["horseNumber"]
                record.update(winnerTop1=rank[0] in winners,
                              winnerTop3=bool(set(rank[:3])&winners),
                              axisTop3Hit=any(axis in o for o in orders),
                              trifectaHit=bool(set(combos)&actuals),
                              stakeYen=100*len(combos),
                              returnYen=sum(price[c] for c in set(combos)&actuals) if set(price)==actuals else None)
                # Dead heats are scored for ticket payoff; skip single-winner proper scores.
                if len(winners)==1:
                    winner=next(iter(winners))
                    record.update(logloss=-math.log(win[winner]),
                                  brier=sum((v-int(n==winner))**2 for n,v in win.items()))
            rows.append(record)
    owners=sorted({r["circuit"] for r in rows})
    grouped={owner:{arm:summarize([r for r in rows if r["circuit"]==owner and r["arm"]==arm])
                    for arm in ARMS} for owner in owners}
    by_date={owner:{day:{arm:summarize([r for r in rows if r["circuit"]==owner and r["date"]==day and r["arm"]==arm])
                        for arm in ARMS}
                    for day in sorted({r["date"] for r in rows if r["circuit"]==owner})}
             for owner in owners}
    return {"schema":"arvexq-stage64-evaluation-1","byCircuit":grouped,"byDate":by_date,
            "resultSha256":digest(results),"rows":rows,
            "independentlyVerifiedPreoff":independently_verified,
            "resultSourceAuthentication":"caller-supplied-saved-official-labels-not-independently-refetched",
            "productionEligible":False,"interpretation":"exploratory-known-data" if not independently_verified else
                "preoff-byte-availability-verified; scientific/model independence requires protocol review"}
