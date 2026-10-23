from bs4 import BeautifulSoup

from arvexq.ingest.payout_parser import parse_payouts


def test_payout_parser_preserves_existing_kind_aliases_and_amounts():
    soup = BeautifulSoup(
        """
        <table>
          <tr><th>単勝</th><td>1</td><td>120円</td></tr>
          <tr><th>枠複</th><td>1-2</td><td>1,230円</td></tr>
          <tr><th>三連単</th><td>1-2-3</td><td>9,870円</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "単勝", "combination": "1", "amount": 120},
        {"type": "枠連", "combination": "1-2", "amount": 1230},
        {"type": "3連単", "combination": "1-2-3", "amount": 9870},
    ]


def test_payout_parser_accepts_line_break_cells_without_inventing_rows():
    soup = BeautifulSoup(
        "<table><tr><th>ワイド</th><td>1-2<br>2-3</td><td>540円<br>760円</td></tr></table>",
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "ワイド", "combination": "1-2", "amount": 540},
        {"type": "ワイド", "combination": "2-3", "amount": 760},
    ]
