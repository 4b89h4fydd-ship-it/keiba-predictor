"""Existing saved-payload version and envelope eligibility; no schema migration."""
VERSION='arvexq-full-payload-v1'


def valid_envelope(ref):
    return ref.get('version')==VERSION and 0<int(ref.get('bytes',0))<=100000000
