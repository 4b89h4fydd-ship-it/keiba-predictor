"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_track_from_cname(cname:str)->str:
    return jra_race_track(cname,JRA_TRACK_CODES)
