"""Independent roster-only cross-checks; target results are never model inputs."""
from bs4 import BeautifulSoup


def check(race, html, provider, source):
    soup=BeautifulSoup(html,'html.parser')
    if provider=='jra_official_result':
        rows=soup.select('table.striped tbody tr')
        roster=[{'number':int(row.select_one('td.num').get_text(strip=True)),
                 'name':row.select_one('td.horse').get_text(strip=True)} for row in rows]
    elif provider=='rakuten_result':
        rows=soup.select('table.dataTable tbody.record > tr')
        roster=[{'number':int(row.select_one('td.number').get_text(strip=True)),
                 'name':row.select_one('td.horse').get_text(strip=True)} for row in rows]
    else:
        raise ValueError('unsupported roster source')
    expected=sorted((h['number'],h['name']) for h in race['horses'])
    observed=sorted((h['number'],h['name']) for h in roster)
    if expected!=observed or not roster:
        raise ValueError('independent published roster mismatch')
    return {'race_id':race['id'],'card_horses':len(expected),'independent_horses':len(observed),
            'exact_number_name_match':True,'fields_read':['number','name'],
            'results_not_passed_to_analysis':True,'source':source}
