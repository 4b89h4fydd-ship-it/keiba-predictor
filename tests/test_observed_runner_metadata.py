"""Published runner identity/affiliation facts must not be filled by guessing."""
import pytest
from bs4 import BeautifulSoup

from arvexq.ingest.entry_fields import affiliation, horse_number, frame_number
from arvexq.ingest.entry_fields.netkeiba import parse_row
from arvexq.ingest.field_normalization import _scratch_status
from arvexq.ingest.runner_cancellation import extract as cancellation
from arvexq.ingest.runner_exclusion import extract as exclusion
from arvexq.forecast.inputs import prediction_input


def row(extra="", trainer="", name="実馬"):
    return BeautifulSoup('<table><tr><td class="HorseInfo"><div class="Horse02"><a>'
                         + name + '</a></div></td><td class="Trainer">' + trainer
                         + '</td>' + extra + '</tr></table>', 'html.parser').tr


@pytest.mark.parametrize('number', range(1,19))
def test_observed_horse_number_range(number):
    assert horse_number.extract(row(f'<span id="odds-1_{number:02d}"></span>')) == number


def test_missing_horse_number_does_not_borrow_row_order():
    assert horse_number.extract(row(), index=7) == 0
    assert parse_row(row(), index=7) is None
    assert horse_number.extract(row('<span id="odds-1_99"></span>')) == 0


@pytest.mark.parametrize('value', ['-1', '19', '100', '1.0', '不明'])
def test_invalid_numeric_cell_does_not_become_a_different_horse(value):
    assert horse_number.extract(row('<td class="Umaban">' + value + '</td>')) == 0


def test_unpublished_frame_is_not_calculated_from_horse_number():
    observed = row('<td class="Umaban">18</td>')
    assert parse_row(observed)['frameNumber'] == 0
    assert frame_number.extract(row('<td class="Waku9">9</td>')) == 0
    for number in range(1,9):
        assert frame_number.extract(row(f'<td class="Waku{number}">{number}</td>')) == number


@pytest.mark.parametrize('value,expected', [
    ('美浦・調教師名','美浦'), ('調教師 名 (栗東)','栗東'),
    ('調教師（本会外）','本会外'), ('大井 調教師','大井'),
    ('愛知・調教師','愛知'), ('美浦田という氏名',''), ('調教師名',''), (None,''),
])
def test_affiliation_requires_a_published_label(value, expected):
    assert affiliation.from_text(value) == expected


def test_composed_card_retains_trainer_and_only_observed_affiliation():
    observed = row('<td class="Umaban">1</td>', trainer='調教師 (美浦)')
    parsed = parse_row(observed)
    assert parsed['trainer'] == '調教師 (美浦)' and parsed['affiliation'] == '美浦'
    absent = row('<td class="Umaban">1</td>', trainer='調教師', name='美浦という馬名')
    assert parse_row(absent)['affiliation'] == ''


def test_observed_frame_and_affiliation_cross_the_input_boundary_without_scoring():
    original = {'horses': [{'horseNumber': 1, 'frameNumber': 1, 'affiliation': '美浦',
                            'mark': 'retired', 'score': 99}, {'horseNumber': 2}]}
    data = prediction_input(original)
    assert data['horses'][0] == {'horseNumber': 1, 'frameNumber': 1, 'affiliation': '美浦'}
    assert data['horses'][1] == {'horseNumber': 2}
    data['horses'][0]['affiliation'] = '栗東'
    assert original['horses'][0]['affiliation'] == '美浦'


@pytest.mark.parametrize('value,status', [
    ('出走取消','出走取消'), ('取消','出走取消'), ('欠場','欠場'),
    ('競走除外','除外'), ('除外','除外'), ('取消・競走除外','除外'),
    ('競走中止',''), ('失格',''), ('出走',''), ('',''), (None,''),
])
def test_cancel_and_exclusion_keep_existing_status_precedence(value, status):
    assert _scratch_status(value) == status
    assert exclusion(value) == ('除外' if value and '除外' in value else '')
    if value and '取消' in value:
        assert cancellation(value) == '出走取消'
