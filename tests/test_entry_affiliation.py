from bs4 import BeautifulSoup
from arvexq.ingest.entry_fields.affiliation import extract

def test_affiliation_observed_prefix_only():
    row = BeautifulSoup('<tr><td class="Horse_Info"><div class="Horse05"><a>栗東・調教師</a></div></td></tr>', "html.parser")
    assert extract(row) == "栗東"
