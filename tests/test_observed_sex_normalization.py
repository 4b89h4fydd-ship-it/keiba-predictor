"""Independent observed-sex contract tests (no app boot)."""
import pytest

from arvexq.ingest.entry_fields.sex import normalize
from arvexq.ingest.field_normalization import _normalize_sex


@pytest.mark.parametrize("raw,expected", [
    ("牡", "牡"), ("牝", "牝"), ("セ", "セ"),
    ("セン", "セ"), ("騸", "セ"), (" 牡 ", "牡"),
    ("　牝　", "牝"), ("", ""), (None, ""),
    ("不明", ""), ("-", ""), ("?", ""),
    ("雄", ""), ("雌", ""), ("牡3", ""),
])
def test_observed_sex_contract(raw, expected):
    assert normalize(raw) == expected
    assert _normalize_sex(raw) == expected
