from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class DataBankResult:
    source: str
    horse_key: str
    data: dict[str, Any] = field(default_factory=dict)
    observed_at: str | None = None
    confidence: float = 1.0
    raw_id: str | None = None


class DataBankAdapter(Protocol):
    """Contract for every external horse/race data source.

    Adapters fetch/parse only. They must not decide prediction scores.
    """

    name: str

    def lookup_horse(self, horse: dict[str, Any], race: dict[str, Any]) -> DataBankResult | None: ...
