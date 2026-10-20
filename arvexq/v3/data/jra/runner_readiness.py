"""JRA-only read-only runner evidence; no retrieval or model execution."""
from arvexq.v3.data.runner_readiness import read_runner_readiness as _read

def read(detail: dict):
    return _read(detail, "jra")
