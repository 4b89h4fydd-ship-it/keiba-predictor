from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BacktestSummary:
    races: int = 0
    honmei_win_hits: int = 0
    mark_top3_hits: int = 0
    trifecta_hits: int = 0
    stake: float = 0.0
    payout: float = 0.0
    max_payout: float = 0.0
    segments: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def honmei_win_rate(self) -> float:
        return self.honmei_win_hits / self.races if self.races else 0.0

    @property
    def trifecta_hit_rate(self) -> float:
        return self.trifecta_hits / self.races if self.races else 0.0

    @property
    def roi(self) -> float:
        return self.payout / self.stake if self.stake else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "races": self.races,
            "honmeiWinHits": self.honmei_win_hits,
            "honmeiWinRate": self.honmei_win_rate,
            "markTop3Hits": self.mark_top3_hits,
            "trifectaHits": self.trifecta_hits,
            "trifectaHitRate": self.trifecta_hit_rate,
            "stake": self.stake,
            "payout": self.payout,
            "roi": self.roi,
            "maxPayout": self.max_payout,
            "segments": self.segments,
        }


def segment_key(race: dict[str, Any]) -> str:
    circuit = str(race.get("circuit") or race.get("source") or "unknown")
    track = str(race.get("track") or "unknown")
    surface = str(race.get("surface") or "unknown")
    distance = int(float(race.get("distance") or 0))
    field = len(race.get("horses") or [])
    return f"{circuit}|{track}|{surface}|{distance}|{field}"
