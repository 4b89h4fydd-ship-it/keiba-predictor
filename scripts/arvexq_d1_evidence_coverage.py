import argparse, json
from collections import Counter
from pathlib import Path
from arvexq.prediction.past_performance import observed_runs

def measure(bundle):
    totals={}
    for detail in bundle.get('details') or []:
        if not isinstance(detail,dict): continue
        circuit='JRA' if str(detail.get('circuit')) in ('JRA','中央') else 'NAR'
        c=totals.setdefault(circuit,Counter())
        c['races']+=1
        for horse in detail.get('horses') or []:
            if not isinstance(horse,dict): continue
            c['horses']+=1
            runs=observed_runs(horse,detail,limit=5)
            c['horsesWithFiveRuns']+=len(runs)>=5
            for run in runs:
                c['runs']+=1
                for key,fields in {'margin':('marginSeconds','timeBehindWinner','margin','marginText'),'sectionalRank':('last3fRank','last3FRank','last600Rank','last3fPercentile'),'sectionalTime':('last3fSeconds','last3f','last600Seconds'),'opponentLevel':('opponentLevel',)}.items():
                    c[key+'Runs']+=any(run.get(f) not in (None,'',[],{}) for f in fields)
    return {k:dict(v) for k,v in totals.items()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=measure(json.loads(Path(a.input).read_text(encoding='utf-8')))
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('EVIDENCE_COVERAGE='+json.dumps(result,ensure_ascii=False))
