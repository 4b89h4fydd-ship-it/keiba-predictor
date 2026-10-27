"""Acquire the selected real JRA/NAR cases; source facts only, no old app imports."""
import argparse
import json
from pathlib import Path
from .acquire import Fetcher
from .parsers import jra_card, jra_history, nar_card
from .roster_check import check

JRA_URL = 'https://sports.yahoo.co.jp/keiba/race/denma/2508030911'
NAR_URL = 'https://keiba.rakuten.co.jp/race_card/list/RACEID/202510222700000001'


def collect(directory):
    directory = Path(directory)
    fetcher = Fetcher(directory/'sources')
    html, source = fetcher.fetch(JRA_URL)
    jra = jra_card(html, source)
    roster_html, roster_source = fetcher.fetch('https://www.jra.go.jp/datafile/seiseki/g1/kikka/result/kikka2025.html')
    jra['roster_check'] = check(jra, roster_html, 'jra_official_result', roster_source)
    for horse in jra['horses']:
        html, source = fetcher.fetch(horse['history_url'])
        horse['histories'], horse['excluded_same_or_future_rows'], horse['unscored_history'] = jra_history(html, source, jra['date'])
        print('history', horse['number'], horse['name'], len(horse['histories']), flush=True)
    html, source = fetcher.fetch(NAR_URL)
    nar = nar_card(html, source)
    roster_html, roster_source = fetcher.fetch('https://keiba.rakuten.co.jp/race_performance/list/RACEID/202510222700000001')
    nar['roster_check'] = check(nar, roster_html, 'rakuten_result', roster_source)
    for race in (jra, nar):
        target = directory/(race['id']+'.input.json')
        data = json.dumps(race, ensure_ascii=False, indent=2, allow_nan=False)
        if target.exists() and target.read_text() != data:
            raise ValueError('immutable input collision; use a fresh capture directory')
        target.write_text(data)
        print('saved', race['id'], len(race['horses']), flush=True)
    return jra, nar


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    collect(parser.parse_args().directory)
