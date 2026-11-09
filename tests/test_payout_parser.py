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


def test_payout_parser_keeps_nar_frame_exacta_out_of_quinella():
    # keiba.go.jp payout tables list 枠連単 (frame exacta) between
    # 馬連複 and 馬連単 at the tracks that sell it. The 枠連単 row used
    # to be read as a continuation of the 馬連 section, storing its
    # amount as a second 馬連 payout for the same combination
    # (Kawasaki 2026-11-09 1R: 馬連 4-5 at both 330 and 950).
    soup = BeautifulSoup(
        """
        <table>
          <tr><td class="title" rowspan="1">枠連複</td>
              <td class="a">4-5</td><td class="refundMoney">400円</td><td class="c">1人気</td></tr>
          <tr><td class="title" rowspan="1">馬連複</td>
              <td class="a">4-5</td><td class="refundMoney">330円</td><td class="c">1人気</td></tr>
          <tr><td class="title" rowspan="1">枠連単</td>
              <td class="a">4-5</td><td class="refundMoney">950円</td><td class="c">1人気</td></tr>
          <tr><td class="title" rowspan="1">馬連単</td>
              <td class="a">4-5</td><td class="refundMoney">640円</td><td class="c">1人気</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "枠連", "combination": "4-5", "amount": 400},
        {"type": "馬連", "combination": "4-5", "amount": 330},
        {"type": "枠連単", "combination": "4-5", "amount": 950},
        {"type": "馬単", "combination": "4-5", "amount": 640},
    ]


def test_payout_parser_never_stores_one_combination_twice():
    # The same pool listed twice with different amounts (an interim
    # table and a final table) must collapse to one row carrying the
    # final amount; an exact repeat is a no-op.
    soup = BeautifulSoup(
        """
        <table>
          <tr><th>馬連</th><td>4-5</td><td>330円</td></tr>
          <tr><th>馬連</th><td>4-5</td><td>950円</td></tr>
          <tr><th>馬連</th><td>4-5</td><td>950円</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "馬連", "combination": "4-5", "amount": 950},
    ]


def test_payout_parser_unknown_section_does_not_inherit_previous_pool():
    # A section label the parser does not know must not have its rows
    # attributed to the pool above it.
    soup = BeautifulSoup(
        """
        <table>
          <tr><td class="title">馬連複</td><td>4-5</td><td>330円</td></tr>
          <tr><td class="title">重勝単</td><td>4-5</td><td>950円</td></tr>
          <tr><td class="title">馬連単</td><td>4-5</td><td>640円</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "馬連", "combination": "4-5", "amount": 330},
        {"type": "馬単", "combination": "4-5", "amount": 640},
    ]


def test_payout_parser_continuation_rows_keep_their_pool():
    # Multi-row pools list the label once (rowspan); the following
    # rows open with the combination and belong to the same pool.
    soup = BeautifulSoup(
        """
        <table>
          <tr><td class="title" rowspan="3">複勝</td><td>4</td><td>110円</td><td>2人気</td></tr>
          <tr><td>5</td><td>100円</td><td>1人気</td></tr>
          <tr><td>8</td><td>160円</td><td>4人気</td></tr>
        </table>
        """,
        "html.parser",
    )
    assert parse_payouts(soup) == [
        {"type": "複勝", "combination": "4", "amount": 110},
        {"type": "複勝", "combination": "5", "amount": 100},
        {"type": "複勝", "combination": "8", "amount": 160},
    ]
