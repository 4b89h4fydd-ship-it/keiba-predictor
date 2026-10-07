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


def _jra_history_adapter(namespace: dict[str, Any]):
    profile_runs = _pick(namespace, "_jra_profile_runs")
    if profile_runs is None:
        return None

    def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        cname = str(
            horse.get("_jraHorseCname")
            or horse.get("jraHorseCname")
            or horse.get("name")
            or ""
        ).strip()
        date = str(race.get("date") or "")
        if not cname or not date:
            return {}
        runs = profile_runs(cname, date, int(limit or 5))
        return {"recentRaces": runs or []}

    return fetch


def _nar_store_adapters(namespace: dict[str, Any]):
    store_cls = namespace.get("NarStore")
    if not callable(store_cls):
        return None, None
    holder: dict[str, Any] = {}

    def store():
        if "value" not in holder:
            holder["value"] = store_cls()
        return holder["value"]

    def history(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        name = str(horse.get("name") or "").strip()
        date = str(race.get("date") or "")
        if not name or not date:
            return {}
        db = store()
        return {
            "recentRaces": db.recent_races(name, date, int(limit or 5)),
            "prizeMoneyAtRace": db.prize_before(name, date),
        }

    def connections(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        del limit
        date = str(race.get("date") or "")
        track = str(race.get("track") or "")
        condition = str(race.get("condition") or "不明")
        try:
            distance = int(race.get("distance") or 0)
        except (TypeError, ValueError):
            distance = 0
        jockey = str(horse.get("jockey") or "").strip()
        trainer = str(horse.get("trainer") or "").strip()
        db = store()
        out: dict[str, Any] = {}
        if jockey:
            out["jockeyStats"] = db.stats("jockey", jockey, date)
            out["jockeyProfile"] = db.role_profile("jockey", jockey, date, track, distance, condition)
        if trainer:
            out["trainerStats"] = db.stats("trainer", trainer, date)
            out["trainerProfile"] = db.role_profile("trainer", trainer, date, track, distance, condition)
        return out

    return history, connections


def register_legacy_sources(namespace: dict[str, Any]) -> dict[str, list[str]]:
    """Bridge proven legacy fetchers into one multi-source registry.

    Fetcher signatures are normalised for the new fallback enrichment lane:
    (horse, race, limit). Missing evidence can therefore fan out across every
    capable provider without the UI knowing which backend supplied it.
    """
    jra = build_jra_source(
        schedule=_pick(namespace, "fetch_jra_official", "fetch_central_feed"),
        race_detail=_pick(namespace, "_jra_parse_race"),
        horse_history=_jra_history_adapter(namespace),
        results=_pick(namespace, "_jra_parse_result"),
        track_weather=_pick(namespace, "_jra_fetch_environment"),
    )
    if jra.fetchers:
        registry.register(jra)

    nar_history, nar_connections = _nar_store_adapters(namespace)
    nar = build_nar_source(
        schedule=_pick(namespace, "nar_race_summaries"),
        race_detail=_pick(namespace, "nar_race_detail"),
        horse_history=nar_history,
        odds=_pick(namespace, "_nar_live_odds"),
        payouts=_pick(namespace, "_fetch_nar_payouts_only"),
        track_weather=_pick(namespace, "_nar_fetch_environment"),
        jockey_trainer=nar_connections,
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
