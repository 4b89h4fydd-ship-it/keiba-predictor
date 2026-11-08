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


def test_payout_parser_reads_jra_refund_dl_lines_with_own_amounts():
    # JRA official result pages carry payouts in a refund_area <dl>,
    # one .line per payout row, each with its own .num/.yen/.pop.
    # The popularity number in .pop must never leak into a combination,
    # and multi-row types must pair each combination with its own amount.
    soup = BeautifulSoup(
        """
        <div class="refund_area">
          <ul><li class="place"><dl><dt>複勝</dt><dd>
            <div class="line"><div class="num">6</div>
              <div class="yen">1,960<span class="unit">円</span></div>
              <div class="pop">15<span>番人気</span></div></div>
            <div class="line"><div class="num">15</div>
              <div class="yen">1,020<span class="unit">円</span></div>
              <div class="pop">12<span>番人気</span></div></div>
            <div class="line"><div class="num">12</div>
              <div class="yen">1,200<span class="unit">円</span></div>
              <div class="pop">13<span>番人気</span></div></div>
          </dd></dl></li>
          <li class="wide"><dl><dt>ワイド</dt><dd>
            <div class="line"><div class="num">6-15</div>
              <div class="yen">29,720<span class="unit">円</span></div>
              <div class="pop">133<span>番人気</span></div></div>
            <div class="line"><div class="num">6-12</div>
              <div class="yen">35,470<span class="unit">円</span></div>
              <div class="pop">140<span>番人気</span></div></div>
          </dd></dl></li>
          <li class="sanrentan"><dl><dt>3連単</dt><dd>
            <div class="line"><div class="num">6-15-12</div>
              <div class="yen">12,065,300<span class="unit">円</span></div>
              <div class="pop">4608<span>番人気</span></div></div>
          </dd></dl></li></ul>
        </div>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "複勝", "combination": "6", "amount": 1960},
        {"type": "複勝", "combination": "15", "amount": 1020},
        {"type": "複勝", "combination": "12", "amount": 1200},
        {"type": "ワイド", "combination": "6-15", "amount": 29720},
        {"type": "ワイド", "combination": "6-12", "amount": 35470},
        {"type": "3連単", "combination": "6-15-12", "amount": 12065300},
    ]


def test_payout_parser_regroups_netkeiba_per_number_combination_cells():
    # netkeiba's Payout_Detail_Table lists each number of a combination
    # on its own line in the combination cell; the numbers belong to
    # arity-sized combinations in cell order, one per amount line.
    soup = BeautifulSoup(
        """
        <table class="Payout_Detail_Table">
          <tr><th>枠連</th><td>4<br>7</td><td>340円</td><td>1人気</td></tr>
          <tr><th>馬連</th><td>7<br>14</td><td>420円</td><td>2人気</td></tr>
          <tr><th>ワイド</th><td>7<br>14<br>3<br>7<br>3<br>14</td>
              <td>210円<br>880円<br>470円</td><td>1人気<br>10人気<br>5人気</td></tr>
          <tr><th>3連単</th><td>7<br>14<br>3</td><td>14,560円</td><td>37人気</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "枠連", "combination": "4-7", "amount": 340},
        {"type": "馬連", "combination": "7-14", "amount": 420},
        {"type": "ワイド", "combination": "7-14", "amount": 210},
        {"type": "ワイド", "combination": "3-7", "amount": 880},
        {"type": "ワイド", "combination": "3-14", "amount": 470},
        {"type": "3連単", "combination": "7-14-3", "amount": 14560},
    ]


def test_payout_parser_drops_combinations_with_wrong_arity_for_type():
    soup = BeautifulSoup(
        """
        <table>
          <tr><th>ワイド</th><td>5</td><td>540円</td></tr>
          <tr><th>三連単</th><td>1-2</td><td>9,870円</td></tr>
          <tr><th>単勝</th><td>1-2</td><td>120円</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == []


def test_payout_parser_accepts_line_break_cells_without_inventing_rows():
    soup = BeautifulSoup(
        "<table><tr><th>ワイド</th><td>1-2<br>2-3</td><td>540円<br>760円</td></tr></table>",
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "ワイド", "combination": "1-2", "amount": 540},
        {"type": "ワイド", "combination": "2-3", "amount": 760},
    ]
