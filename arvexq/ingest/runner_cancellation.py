"""Observed cancellation/absence labels only; no inference from missing data."""


def extract(value: str | None) -> str:
    if value and "取消" in value:
        return "出走取消"
    if value and "欠場" in value:
        return "欠場"
    return ""
