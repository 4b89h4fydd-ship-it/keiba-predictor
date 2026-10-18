"""Observed race exclusion label only; other outcomes are not exclusions."""


def extract(value: str | None) -> str:
    return "除外" if value and "除外" in value else ""
