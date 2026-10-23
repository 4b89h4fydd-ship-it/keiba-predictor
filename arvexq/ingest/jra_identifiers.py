"""Backward-compatible JRA identifier interface backed by independent field modules.

The application's established imports remain stable; date and race number
are parsed independently and neither may infer the other's missing value.
"""
from arvexq.ingest.race_fields.date import extract as _jra_date_from_cname
from arvexq.ingest.race_fields.race_number import extract as _jra_race_no_from_cname
