"""JRA observed clock only; no betting/model calculations."""
from arvexq.v3.data.result_facts import finish_field as _field


def read(detail: dict) -> list[dict]:
    return _field(detail, "jra", "clock")
