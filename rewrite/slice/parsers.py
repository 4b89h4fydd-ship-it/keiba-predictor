"""New parsers for public cards and historical fact tables. Never reads predictions."""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def text(node):
    return node.get_text(' ', strip=True) if node else ''


def number(value, pattern=r'[-+]?\d+(?:\.\d+)?'):
    match = re.search(pattern, value or '')
    return float(match.group()) if match else None


def clock(value):
    match = re.search(r'(\d+):(\d{2}\.\d)', value)
    return int(match[1])*60 + float(match[2]) if match else None


def require(value, message):
    if not value:
        raise ValueError(message)
    return value


def jra_card(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    title = text(soup.select_one('.hr-predictRaceInfo__title'))
    require('菊花賞' in title, 'unexpected JRA card')
    horses = []
    for row in soup.select('tbody[data-denma-sort-body] > tr'):
        cells = row.find_all('td', recursive=False)
        require(len(cells) == 8, 'JRA card schema changed')
        link = require(cells[2].select_one('a[href*="/horse/"]'), 'horse link absent')
        pedigree = [text(p) for p in cells[5].select('p')]
        sex_age = re.search(r'([牡牝セせ])(\d+)', text(cells[2]))
        horses.append({'number': int(text(cells[1])), 'frame': int(text(cells[0])),
                       'horse_id': link['href'].strip('/').split('/')[-1], 'name': text(link),
                       'sex': sex_age[1] if sex_age else None,
                       'age': int(sex_age[2]) if sex_age else None,
                       'jockey': text(cells[3].select_one('a')), 'carried_weight': number(text(cells[3].select_one('p'))),
                       'trainer': text(cells[4].select_one('a')), 'body_weight': number(text(cells[6])),
                       'pedigree': pedigree or None,
                       'odds': number(text(cells[7].select_one('span'))),
                       'history_url': urljoin(source['url'], link['href']), 'cancelled': False,
                       'source': source, 'histories': []})
    # Independent published count in race overview, not a configured constant.
    info = text(soup.select_one('.hr-predictRaceInfo'))
    head_count = re.search(r'(\d+)頭', info)
    require('3000m' in text(soup) and len(horses) >= 2, 'course or field absent')
    return {'id':'jra-2025-10-26-京都-11', 'date':'2025-10-26', 'circuit':'中央',
            'track':'京都', 'race_number':11, 'title':title, 'surface':'芝', 'distance':3000,
            'starts_at':'2025-10-26T15:40:00+09:00', 'declared_count':int(head_count[1]) if head_count else len(horses),
            'field_count_basis':'published_card_rows; independently cross-check official roster',
            'source':source, 'horses':horses}


def jra_history(html, source, cutoff):
    soup = BeautifulSoup(html, 'html.parser')
    histories = []
    excluded = 0
    unscored = []
    for row in soup.select('tr.hr-table__row'):
        date_node = row.select_one('td.hr-table__data--date')
        if not date_node:
            continue
        date = text(date_node).replace('/', '-')
        if date >= cutoff:
            excluded += 1
            continue
        cells = row.find_all('td', recursive=False)
        require(len(cells) == 9, 'JRA history schema changed')
        course = text(cells[1].select_one('p'))
        course_match = re.search(r'(\S+)\s+([芝ダ障])(\d+)m\s+(\d+)頭', course)
        require(course_match, 'history course absent')
        finish = text(cells[2])
        if not finish.isdigit():
            unscored.append({'date':date,'status':finish,'reason':'non_numeric_finish_not_scored','source':source})
            continue
        corners = text(cells[8]).split(' ')[0]
        time_text = text(cells[7])
        margin = re.search(r'\(([+-]?\d+(?:\.\d+)?)\)', time_text)
        link = cells[1].select_one('a')
        histories.append({'date':date, 'race_key':urljoin(source['url'], link['href']) if link else None,
                          'title':text(link), 'track':course_match[1], 'surface':course_match[2],
                          'distance':int(course_match[3]), 'field_size':int(course_match[4]),
                          'finish':int(finish), 'time_seconds':clock(time_text),
                          'margin_seconds':float(margin[1]) if margin else None,
                          'corners':[int(x) for x in corners.split('-')] if re.fullmatch(r'\d+(?:-\d+)+', corners) else None,
                          'last3f':number(text(cells[8].select_one('p'))),
                          'class':text(cells[1].select_one('span')) or text(link),
                          'opponent':None, 'going':None, 'source':source})
    return histories, excluded, unscored


def nar_card(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    require('2025/10/22 1R' in text(soup.title) and '園田' in text(soup.title), 'unexpected NAR card')
    horses = []
    frame = None
    for row in soup.select('table.dataTable tbody > tr'):
        if not row.select_one('td.number'):
            continue
        frame_node = row.find('th', recursive=False)
        if frame_node and text(frame_node).isdigit():
            frame = int(text(frame_node))
        name_cell = row.select_one('td.name')
        link = require(name_cell.select_one('.mainHorse a'), 'horse identity absent')
        profile = text(row.select_one('td.profile'))
        age = re.search(r'([牡牝セせ])(\d+)', profile)
        jockey = row.select_one('td.profile a')
        lines = [x.strip() for x in row.select_one('td.profile').stripped_strings]
        history = []
        unscored = []
        for cell in row.select('td.race'):
            value = text(cell)
            date = re.search(r'(\d{2})\.(\d{2})\.(\d{2})', value)
            if not date:
                continue
            date = f'20{date[1]}-{date[2]}-{date[3]}'
            if date >= '2025-10-22':
                raise ValueError('NAR future history in card')
            course = re.search(r'(\d{3,4})([右左])([ダ芝])', value)
            finish = text(cell.select_one('.place'))
            if not finish.isdigit():
                unscored.append({'date':date,'status':finish,'reason':'historical_cancellation_or_nonfinish_not_scored','source':source})
                continue
            route = cell.select_one('.raceName a')
            margin = re.search(r'\d+:\d{2}\.\d\s*\(([+-]?\d+(?:\.\d+)?)\)', value)
            trailing = re.search(r'(\d+\.\d)\s+\d+k\s+\d+番', value)
            corner = re.search(r'\b\d+(?:-\d+){1,3}\b', value)
            track_match = re.search(r'(\S+)\s+\d{2}\.\d{2}\.\d{2}', value)
            history.append({'date':date, 'race_key':route['href'] if route else None,
                            'title':text(route), 'track':track_match[1] if track_match else None,
                            'surface':course[3] if course else None,
                            'distance':int(course[1]) if course else None,
                            'field_size':int(number(text(cell.select_one('.numberInfo')))),
                            'finish':int(finish), 'time_seconds':clock(value),
                            'margin_seconds':float(margin[1]) if margin else None,
                            'corners':[int(x) for x in corner[0].split('-')] if corner else None,
                            'last3f':float(trailing[1]) if trailing else None,
                            'class':text(route), 'opponent':list(cell.stripped_strings)[-1],
                            'going':text(cell.select_one('.stateInfo')) or None, 'source':source})
        pedigree = [x.strip() for x in name_cell.stripped_strings]
        horses.append({'number':int(text(row.select_one('td.number'))), 'frame':frame,
                       'horse_id':link['href'].split('/')[-1], 'name':text(link),
                       'sex':age[1] if age else None, 'age':int(age[2]) if age else None,
                       'jockey':text(jockey), 'carried_weight':number(profile, r'\d{2}\.\d'),
                       'trainer':lines[-1] if lines else None,
                       'body_weight':number(text(row.select_one('td.weightDistance'))),
                       'pedigree':pedigree[:3], 'odds':number(text(name_cell.select_one('.rate'))),
                       'cancelled':False, 'unscored_history':unscored, 'histories':history, 'source':source})
    return {'id':'nar-2025-10-22-園田-01', 'date':'2025-10-22', 'circuit':'地方',
            'track':'園田', 'race_number':1, 'title':'Ｃ３二 ３歳以上', 'surface':'ダ', 'distance':1400,
            'starts_at':'2025-10-22T10:40:00+09:00', 'declared_count':len(horses),
            'field_count_basis':'published_card_rows; no independent declared-count field',
            'source':source, 'horses':horses}
