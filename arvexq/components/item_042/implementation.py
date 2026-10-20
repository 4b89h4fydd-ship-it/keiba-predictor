"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_parse_past_cell(cell, cutoff:str) -> dict | None:
    # Provider-specific identity stays here; each observed field is parsed in
    # its independently testable extractor and composed without forecasts.
    result_cname=_jra_attr_cname(cell,JRA_RESULT_CNAME_RE)
    rid=("jraresult-"+base64.urlsafe_b64encode(result_cname.encode()).decode().rstrip("=")) if result_cname else ""
    tracks=list(JRA_TRACK_CODES.values())+["門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"]
    return parse_jra_history_cell(cell,cutoff,tracks,race_id=rid)
