"""Provider DOM contracts: individual fields, missing values and replacement."""
import copy
import pytest
from bs4 import BeautifulSoup
from arvexq.ingest.entry_fields import horse_number, frame_number, name, sex, age, carried_weight, jockey, trainer, body_weight, body_weight_change, win_odds, popularity, status
from arvexq.ingest.entry_fields.netkeiba import parse_row

HTML = '''<table><tr><td class="Waku3"></td><td class="Horse_Info"><dt class="Horse"><a>テストホース</a></dt><dd class="Age">牝4</dd><dd class="Jockey"><em>騎手名</em>54.5</dd><div class="Horse05"><a>美浦・調教師名</a></div><div class="Weight">480(+6)</div></td><td><span id="odds-1_05">12.3</span><span id="ninki-1_05">7</span></td></tr></table>'''

def row(html=HTML): return BeautifulSoup(html, 'html.parser').find('tr')

@pytest.mark.parametrize('module,expected', [(horse_number,5),(frame_number,3),(name,'テストホース'),(sex,'牝'),(age,4),(carried_weight,54.5),(jockey,'騎手名'),(trainer,'調教師名'),(body_weight,480),(body_weight_change,6),(win_odds,12.3),(popularity,7),(status,'')])
def test_field_extracts_only_its_own_observation(module,expected):
    source=row();before=str(source)
    assert module.extract(source)==expected
    assert str(source)==before

@pytest.mark.parametrize('module,expected', [(horse_number,0),(frame_number,0),(name,''),(sex,''),(age,0),(carried_weight,0.0),(jockey,''),(trainer,''),(body_weight,None),(body_weight_change,None),(win_odds,None),(popularity,None),(status,'')])
def test_missing_field_never_borrows_another_field(module,expected):
    assert module.extract(row('<table><tr><td>不明</td></tr></table>'))==expected

def test_composition_and_adapter_replacement_are_independent():
    normal=parse_row(row());changed=parse_row(row(),extractors={'bodyWeightChange':lambda _:None})
    assert changed==dict(normal,bodyWeightChange=None)
    assert normal['name']=='テストホース' and normal['recentRaces']==[]
    assert normal['horseNumber']==5 and normal['frameNumber']==3
    assert parse_row(row('<table><tr><td></td></tr></table>')) is None

def test_old_dom_fallback_and_cancelled_runner():
    source=row('<table><tr><td class="Waku2">2</td><td class="Umaban">3</td><td class="HorseInfo"><div class="Horse02"><a>テスト</a></div></td><td class="Barei">セ6</td><td class="Jockey"><a>騎手B</a>57.0</td><td class="Trainer">調教師B</td><td class="Weight">510(-4)</td><td>競走除外</td></tr></table>')
    result=parse_row(source)
    assert result['horseNumber']==3 and result['sex']=='セ' and result['age']==6
    assert result['status']=='除外' and result['scratched']
    assert result['bodyWeightChange']==-4 and result['jockey']=='騎手B'

def test_app_uses_field_composition():
    import app
    assert app._nk_row_horse is parse_row
