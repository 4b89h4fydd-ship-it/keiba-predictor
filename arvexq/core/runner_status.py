from __future__ import annotations

from typing import Any

SCRATCH_STATUSES = {"取消", "出走取消", "競走取消", "除外", "競走除外", "欠場"}


def normalize_runner_status(value: Any, *, scratched: bool = False, withdrawn: bool = False) -> str:
    s = str(value or "").strip()
    if "競走除外" in s or s == "除外":
        return "競走除外"
    if "出走取消" in s or "競走取消" in s or s == "取消":
        return "出走取消"
    if "欠場" in s:
        return "欠場"
    if scratched or withdrawn:
        return "出走取消"
    return s


def is_inactive_runner(horse: dict[str, Any] | None) -> bool:
    if not isinstance(horse, dict):
        return False
    if horse.get("scratched") or horse.get("withdrawn"):
        return True
    return normalize_runner_status(horse.get("status")) in {"出走取消", "競走除外", "欠場"}
