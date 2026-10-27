import argparse
import json
from pathlib import Path
from .analyze import analyze
from .store import Store


def run(directory, database):
    store = Store(database)
    summaries = []
    try:
        for path in sorted(Path(directory).glob('*.input.json')):
            race = json.loads(path.read_text())
            analysis = analyze(race)
            saved = store.save(race, analysis)
            assert saved['race']==race and saved['analysis']==analysis
            summaries.append({'race_id':race['id'],'horses':len(race['horses']),
                              'history_rows':sum(len(h['histories']) for h in race['horses']),
                              'missing_rate':analysis['quality']['missing_rate'],
                              'missing':analysis['quality']['missing'],'expected':analysis['quality']['expected'],
                              'marks':{r['number']:r['mark'] for r in analysis['rows'] if r['mark']},
                              'receipt':saved['receipt']})
            target = Path(directory)/(race['id']+'.response.json')
            target.write_text(json.dumps(saved,ensure_ascii=False,indent=2))
    finally:
        store.close()
    reopened = Store(database)
    try:
        for summary in summaries:
            reloaded = reopened.read(summary['race_id'])
            assert reloaded['receipt']==summary['receipt']
        summaries = [dict(s, reopen_identical=True) for s in summaries]
    finally:
        reopened.close()
    (Path(directory)/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2))
    return summaries


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory',required=True)
    parser.add_argument('--database',required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.directory,args.database),ensure_ascii=False,indent=2))
