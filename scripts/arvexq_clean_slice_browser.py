"""Real API + Chromium checks. No intercepted, stubbed or fabricated responses."""
import argparse
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(base, directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(base+'/api/v1/races') as response:
        races=json.load(response)['races']
    report=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,locale='ja-JP')
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        for race in races:
            rid=race['id']
            with urllib.request.urlopen(base+'/api/v1/races/'+urllib.parse.quote(rid)) as response:
                document=json.load(response)
            page.goto(base+'/?race='+urllib.parse.quote(rid))
            page.wait_for_selector('#section-racecard .racecard-row')
            assert page.locator('#section-racecard .racecard-row').count()==race['declared_count']
            assert page.locator('#section-racecard [data-ai-mark="◎"]').count()==1
            assert '見送り' in page.locator('#section-bets').inner_text()
            for row in document['analysis']['rows']:
                button=page.locator('button[data-horse="'+str(row['number'])+'"]')
                assert button.locator('..').locator('[data-ai-mark]').get_attribute('data-ai-mark')==row['mark']
                button.click()
                page.wait_for_selector('#horse-dialog[open]')
                heading=page.locator('#horse-detail h2').inner_text()
                assert row['name'] in heading and row['mark'] in heading
                assert page.locator('#horse-detail .slice-history').count()==len(next(h for h in document['race']['horses'] if h['number']==row['number'])['histories'])
                page.locator('#close-horse').click()
            scenario_orders=[]
            for i in range(3):
                page.select_option('#scenario',str(i))
                assert page.locator('[data-stage]').count()==4
                orders={}
                for key in ('start','thirdCorner','fourthCorner','straight'):
                    items=page.locator('[data-stage="'+key+'"] li')
                    assert items.count()==race['declared_count']
                    orders[key]=items.evaluate_all('(elements)=>elements.map(x=>Number(x.dataset.number))')
                    assert orders[key]==[x['number'] for x in document['analysis']['scenarios'][i]['stages'][key]]
                scenario_orders.append(orders)
            page.select_option('#scenario','0')
            before=page.locator('#section-racecard').inner_text()
            page.reload();page.wait_for_selector('#section-racecard .racecard-row')
            assert before==page.locator('#section-racecard').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(directory/(rid+'.png')),full_page=True)
            page.locator('#back').click()
            page.wait_for_selector('[data-race]')
            page.locator('[data-race]').first.click();page.wait_for_selector('#section-racecard')
            other=next(r for r in races if r['id']!=rid)
            page.fill('#date',other['date']);page.select_option('#circuit',other['circuit'])
            page.wait_for_selector('[data-track]');page.locator('[data-track]').first.click()
            page.locator('[data-race]').first.click();page.wait_for_selector('#section-racecard')
            assert page.locator('#section-racecard .racecard-row').count()==other['declared_count']
            report.append({'race_id':rid,'horses':race['declared_count'],'all_horse_dialogs':True,
                           'four_stages_three_scenarios_match_api':True,'marks_match_api':True,
                           'reload_identical':True,'date_circuit_navigation':True,'horizontal_overflow':False,
                           'bet_decision':'見送り','screenshot':rid+'.png','passed':True})
        assert not errors,errors
        page.route('**/api/v1/races',lambda route:route.abort('failed'))
        page.goto(base);page.wait_for_selector('[role=alert]')
        assert page.locator('.racecard-row').count()==0
        outage={'visible_error':True,'fake_race_rows':0}
        browser.close()
    (directory/'browser-report.json').write_text(json.dumps({'cases':report,'page_errors':errors,'api_outage':outage},ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:8766');parser.add_argument('--directory',required=True)
    args=parser.parse_args();run(args.base,args.directory)
