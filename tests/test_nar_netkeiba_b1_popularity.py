"""The netkeiba NAR b1 page combines odds and popularity in one header
cell ("オッズ 人気"); the row cell looks like "23.4 6人気". The rank is
the number attached to 人気, never the win-odds integer part."""
import app


def test_b1_combined_cell_popularity_comes_from_ninki(monkeypatch):
    shutuba = "<html><body><table></table></body></html>"
    b1 = """<html><body><table>
    <tr><th>馬番</th><th>チェック</th><th>馬名 年齢 騎手 斤量</th>
    <th>オッズ 人気</th><th>馬体重 (増減)</th></tr>
    <tr><td>1</td><td></td><td>ワローテル 牡3 塩津璃菜 54.0</td>
    <td>23.4 6人気</td><td></td></tr>
    <tr><td>2</td><td></td><td>ニネンエフグミ 牝4 廣瀬航 55.0</td>
    <td>4.0 3人気</td><td></td></tr>
    </table></body></html>"""

    def fake_get(url, timeout, cache):
        return shutuba if "shutuba" in url else b1

    monkeypatch.setattr(app, "_netkeiba_get", fake_get)
    rows = app._nar_netkeiba_preview_rows(
        {"date": "2026-11-04", "track": "園田", "raceNumber": 4}, force=True)
    assert rows[1]["winOdds"] == 23.4
    assert rows[1]["popularity"] == 6
    assert rows[2]["winOdds"] == 4.0
    assert rows[2]["popularity"] == 3
