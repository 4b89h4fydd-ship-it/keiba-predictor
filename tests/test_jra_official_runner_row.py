"""Contracts for official JRA runner-number extraction."""
from bs4 import BeautifulSoup

from arvexq.ingest.jra_official_runner_row import extract


def text_of(cell):
    return cell.get_text(" ", strip=True)


def cells_for(value):
    soup = BeautifulSoup(f"<tr><td>{value}</td><td>枠情報</td><td>馬情報</td></tr>", "html.parser")
    return soup.find("tr").find_all(["th", "td"])


def test_accepts_every_official_horse_number():
    for number in range(1, 19):
        assert extract(cells_for(number), text_of) == (number, 0)


def test_ignores_out_of_range_and_malformed_values():
    for value in ("0", "19", "99", "1.0", "取消", "競走除外", "", "  "):
        assert extract(cells_for(value), text_of) == (0, -1)


def test_checks_only_first_three_cells_and_skips_invalid_candidates():
    soup = BeautifulSoup("<tr><td>0</td><td>19</td><td>18</td><td>1</td></tr>", "html.parser")
    assert extract(soup.find("tr").find_all("td"), text_of) == (18, 2)


def test_empty_and_missing_cells_return_legacy_missing_pair():
    assert extract([], text_of) == (0, -1)


def test_number_index_tracks_the_actual_candidate_cell():
    soup = BeautifulSoup("<tr><td>0</td><td> 7 </td><td>情報</td></tr>", "html.parser")
    assert extract(soup.find("tr").find_all("td"), text_of) == (7, 1)
