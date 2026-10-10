"""Extract only actual acquired odds from a hash-verified saved original."""
import re

SOURCES = {'netkeiba', 'netkeiba実オッズ', 'NAR公式', 'JRA公式', 'NAR公式出馬表'}

def saved_odds(detail, sha256):
    source = detail.get('oddsSource')
    stamp = str(detail.get('oddsUpdatedAt') or '')
    if source not in SOURCES or detail.get('oddsForecast') is True:
        return None
    if re.fullmatch(r'\d{2}:\d{2}:\d{2}', stamp):
        stamp = detail['date'] + 'T' + stamp + '+09:00'
    if not re.match(r'^\d{4}-\d{2}-\d{2}T', stamp):
        return None
    rows = []
    for horse in detail.get('horses') or []:
        if horse.get('oddsForecast') is True or horse.get('oddsSource') not in SOURCES:
            continue
        odds = horse.get('winOdds')
        scratched = bool(horse.get('scratched') or horse.get('withdrawn'))
        if not scratched and not (isinstance(odds, (int, float)) and odds > 0):
            continue
        pop = horse.get('popularity')
        rows.append({'horse_no':horse['horseNumber'], 'horse_name':horse['name'],
                     'win_odds':None if scratched else odds,
                     'popularity':pop if isinstance(pop, int) and pop > 0 else None,
                     'scratched':scratched, 'horse_status':'出走取消' if scratched else '',
                     'oddsSource':horse['oddsSource']})
    if not any(row['win_odds'] for row in rows):
        return None
    return {'ok':True,'race_id':detail['id'],'odds':rows,'oddsSource':source,
            'oddsUpdatedAt':stamp,'sourcePublishedAt':stamp,
            'oddsStatus':'saved','refreshFailed':True,'sourceSnapshotSha256':sha256}
