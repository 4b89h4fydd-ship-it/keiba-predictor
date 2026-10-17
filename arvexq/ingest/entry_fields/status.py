"""Extract and normalize only status from a provider row. Missing values remain absent."""
from .dom import text
from arvexq.ingest.field_normalization import _scratch_status

def extract(row):
    return _scratch_status(text(row))
