"""Research-only audit of saved v9b publications; never recompute a forecast.

Standalone for MotherDuck Flights. Output is append-only, one execution payload.
Timestamps are evidence of publication, not proof of original input availability.
"""
import collections
import datetime as dt
import hashlib
import json
import math
import random
import statistics
import uuid

VERSION = 'arvexq-rewrite-v3-v9b'
DEST = 'arvexq_history_research.main.v9b_saved_audit_v1'


def digest(value):
    # Same value canonicalization as unified_product.canonical_receipt.
    def canonical(v):
        if isinstance(v, float) and v.is_integer() and abs(v) < 2**53:
            return int(v)
        if isinstance(v, dict):
            return {k: canonical(x) for k, x in v.items()}
        if isinstance(v, list):
            return [canonical(x) for x in v]
        return v
    return hashlib.sha256(json.dumps(canonical(value), ensure_ascii=False,
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def receipt_hashes(f):
    # Legacy serialization variants accepted by unified_product.verified.
    value = {k:v for k,v in f.items() if k != 'receiptSha256'}
    float_keys = {'beta','winProbability','top3Probability','winProbabilityRange',
                  'top3ProbabilityRange','abilityScore','pacePressure','probability','odds','expectedValue'}
    def restore(v, key=None):
        if isinstance(v,dict):return {k:restore(x,k) for k,x in v.items()}
        if isinstance(v,list):return [restore(x,key) for x in v]
        return float(v) if key in float_keys and type(v) is int else v
    def raw_digest(v):
        return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,
            separators=(',', ':'),allow_nan=False).encode()).hexdigest()
    return {digest(value),raw_digest(value),raw_digest(restore(value))}


def extract(s):
    f = s.get('unifiedForecast') or {}
    if s.get('track') == '帯広' or '帯広' in str(s.get('id')):
        return None, 'banei'
    if f.get('modelVersion') != VERSION:
        return None, 'no-saved-v9b-publication'
    marker = (s.get('preparedMeta') or {}).get('rewritePublish') or {}
    sha = f.get('receiptSha256')
    if not sha or marker.get('receiptSha256') != sha or sha not in receipt_hashes(f):
        return None, 'receipt-mismatch'
    try:
        post = dt.datetime.fromisoformat(s['date']+'T'+(s.get('startTime') or s['scheduledStartTime'])[:5]+'+09:00')
        capture = dt.datetime.fromisoformat(f['capturedAt'])
        published = dt.datetime.fromisoformat(marker['publishedAt'])
        if not capture.tzinfo or not published.tzinfo or not capture <= published < post:
            return None, 'publication-not-preoff'
    except (ValueError, KeyError, TypeError):
        return None, 'missing-publication-clock'
    if f.get('raceId') != s.get('id') or f.get('raceDate') != s.get('date'):
        return None, 'identity-mismatch'
    result = s.get('result') or {}
    if result.get('status') != '確定':
        return None, 'unsettled'
    rows = f.get('diagnosis') or []
    nos = [int(h['horseNumber']) for h in rows]
    roster = [int(h['horseNumber']) for h in f.get('roster') or []]
    finishes = [(int(h['horseNumber']), int(h['finish'])) for h in result.get('finishers') or [] if str(h.get('finish','')).isdigit() and int(h['finish']) > 0]
    if len(nos)<2 or len(set(nos))!=len(nos) or len(roster)!=len(set(roster)) or set(roster)!=set(nos) or len(finishes)!=len(nos) or set(n for n,_ in finishes)!=set(nos):
        return None, 'incomplete-or-duplicate-roster'
    finish = dict(finishes)
    if len(finish)!=len(finishes) or any(p != 1+sum(q<p for q in finish.values()) for p in finish.values()):
        return None, 'invalid-competition-ranks'
    p = [float(h['winProbability']) for h in rows]
    if any(not math.isfinite(v) or not 0<=v<=1 for v in p) or abs(sum(p)-1)>.002:
        return None, 'invalid-win-distribution'
    # Only rounding normalization. Probability scores are never refitted.
    p = [v/sum(p) for v in p]
    metrics = race_metrics(nos, finishes, p)
    winners = {n for n,v in finishes if v==1}
    order = sorted(range(len(nos)), key=lambda i:(-p[i],nos[i]))
    odds_rows = (f.get('ticketPlan') or {}).get('winExpectedValues') or []
    odds = {int(h['horseNumber']):float(h['odds']) for h in odds_rows}
    market = None
    if len(odds_rows)==len(nos) and set(odds)==set(nos) and all(math.isfinite(v) and v>0 for v in odds.values()):
        inv = [1/odds[n] for n in nos]
        market = race_metrics(nos, finishes, [v/sum(inv) for v in inv])
    return dict(raceId=s['id'], date=s['date'], circuit=s.get('circuit'), fieldSize=len(nos),
        family=f.get('modelFamily'), capturedAt=f['capturedAt'], receiptSha256=sha,
        metrics=metrics, marketMetrics=market, winnerNumbers=sorted(winners), predictedNumber=nos[order[0]],
        diagnosis=rows, failureCause='未特定' if not metrics['top1Win'] else None,
        evidenceClass='saved-publication-preoff-clock-and-receipt; original-input-availability-not-certified'), 'eligible'


def race_metrics(nos, finishes, p):
    finish = dict(finishes)
    order = sorted(range(len(nos)), key=lambda i:(-p[i],nos[i]))
    winners = {n for n,v in finishes if v==1}
    rank = min(k+1 for k,i in enumerate(order) if nos[i] in winners)
    gains = [2**max(0,4-finish[n])-1 for n in nos]
    ideal = sum(v/math.log2(k+2) for k,v in enumerate(sorted(gains,reverse=True)[:3]))
    metrics = dict(top1Win=int(nos[order[0]] in winners), top1Podium=int(finish[nos[order[0]]]<=3), winnerTop3=int(rank<=3), winnerTop5=int(rank<=5), mrr=1/rank,
        ndcg3=sum(gains[i]/math.log2(k+2) for k,i in enumerate(order[:3]))/ideal,
        logLoss=-sum(math.log(max(p[i],1e-15)) for i,n in enumerate(nos) if n in winners)/len(winners),
        brier=sum((v-int(n in winners)/len(winners))**2 for n,v in zip(nos,p)))
    return metrics


def paired_market(rows, draws=2000):
    rows = [r for r in rows if r.get('marketMetrics')]
    days = sorted({r['date'] for r in rows})
    if not rows:
        return {'races':0}
    grouped = {d:[r for r in rows if r['date']==d] for d in days}
    rng=random.Random(20261111); intervals={}
    for k in rows[0]['metrics']:
        diffs=[r['metrics'][k]-r['marketMetrics'][k] for r in rows]
        samples=[]
        if len(days)>=2:
            for _ in range(draws):
                batch=[r for day in rng.choices(days,k=len(days)) for r in grouped[day]]
                samples.append(statistics.mean(r['metrics'][k]-r['marketMetrics'][k] for r in batch))
            samples.sort()
        intervals[k]={'v9bMinusMarket':statistics.mean(diffs),'dayCluster95':[samples[int(.025*draws)],samples[int(.975*draws)]] if samples else None}
    return dict(races=len(rows),days=len(days),resamples=draws,paired=intervals,marketSource='same-receipt ticketPlan.winExpectedValues; normalized inverse odds')


def summarize(rows):
    if not rows:
        return {'races':0}
    return dict(races=len(rows), days=len({r['date'] for r in rows}),
        metrics={k:statistics.mean(r['metrics'][k] for r in rows) for k in rows[0]['metrics']})


def main():
    import duckdb
    c = duckdb.connect('md:')
    before = c.execute('SELECT race_id,sha256 FROM my_db.arvexq_analytics.race_snapshots ORDER BY race_id').fetchall()
    counts = collections.Counter(); rows=[]; ledger=[]
    for (day,) in c.execute('SELECT DISTINCT race_date FROM my_db.arvexq_analytics.race_snapshots ORDER BY 1').fetchall():
        for rid,raw in c.execute('SELECT race_id,CAST(snapshot_json AS VARCHAR) FROM my_db.arvexq_analytics.race_snapshots WHERE race_date=? ORDER BY race_id',[day]).fetchall():
            try:
                row,status=extract(json.loads(raw))
            except (ValueError,TypeError,KeyError,OverflowError):
                row,status=None,'malformed-publication-or-result'
            counts[status]+=1;ledger.append(dict(raceId=rid,status=status))
            if row:rows.append(row)
    payload=dict(productionChanged=False, independentTest=False, counts=dict(counts),ledger=ledger, races=rows,
        summaries={str(circuit):summarize([r for r in rows if r['circuit']==circuit]) for circuit in sorted({r['circuit'] for r in rows})},
        marketComparison={str(circuit):paired_market([r for r in rows if r['circuit']==circuit]) for circuit in sorted({r['circuit'] for r in rows})},
        jra13Plus=summarize([r for r in rows if r['circuit']=='中央' and r['fieldSize']>=13]),
        limitations=['No causal attribution from outcome alone','No same-time challenger comparison yet','No final odds used as preoff market evidence'],
        sourceManifestSha=digest(before), codeSha=hashlib.sha256(open(__file__,'rb').read()).hexdigest())
    assert before==c.execute('SELECT race_id,sha256 FROM my_db.arvexq_analytics.race_snapshots ORDER BY race_id').fetchall()
    execution=str(uuid.uuid4()); encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False)
    c.execute(f'CREATE TABLE IF NOT EXISTS {DEST} (execution_id VARCHAR, payload JSON)')
    c.execute(f'INSERT INTO {DEST} VALUES (?,?)',[execution,encoded])
    restored=c.execute(f'SELECT CAST(payload AS VARCHAR) FROM {DEST} WHERE execution_id=?',[execution]).fetchone()[0]
    assert json.loads(restored)==payload
    print(json.dumps(dict(execution=execution,counts=dict(counts),summaries=payload['summaries'],jra13Plus=payload['jra13Plus'],readbackVerified=True),ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
