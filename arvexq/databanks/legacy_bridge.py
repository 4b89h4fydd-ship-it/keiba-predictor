from __future__ import annotations

from typing import Any

from .jra import build_jra_source
from .nar import build_nar_source
from .netkeiba import build_netkeiba_source
from .registry import registry


def _pick(namespace: dict[str, Any], *names: str):
    for name in names:
        value = namespace.get(name)
        if callable(value):
            return value
    return None


def register_legacy_sources(namespace: dict[str, Any]) -> dict[str, list[str]]:
    """Bridge the current monolith into the modular databank registry.

    This is temporary migration glue: existing proven fetchers stay in app.py while
    callers move to the registry. Each fetcher can then be extracted independently.
    """
    jra = build_jra_source(
        schedule=_pick(namespace, "fetch_jra_official", "fetch_central_feed"),
        race_detail=_pick(namespace, "_jra_parse_race"),
        horse_history=_pick(namespace, "_jra_profile_runs"),
        results=_pick(namespace, "_jra_parse_result"),
        track_weather=_pick(namespace, "_jra_fetch_environment"),
    )
    if jra.fetchers:
        registry.register(jra)

    nar = build_nar_source(
        schedule=_pick(namespace, "nar_race_summaries"),
        race_detail=_pick(namespace, "nar_race_detail"),
        odds=_pick(namespace, "_nar_live_odds"),
        payouts=_pick(namespace, "_fetch_nar_payouts_only"),
        track_weather=_pick(namespace, "_nar_fetch_environment"),
    )
    if nar.fetchers:
        registry.register(nar)

    netkeiba = build_netkeiba_source(
        odds=_pick(namespace, "_netkeiba_live_win_odds"),
        results=_pick(namespace, "_netkeiba_current_result"),
        track_weather=_pick(namespace, "_netkeiba_race_meta"),
    )
    if netkeiba.fetchers:
        registry.register(netkeiba)

    return registry.capability_map()
