from __future__ import annotations

from typing import Any
from threading import local

from .jra import build_jra_source
from .nar import build_nar_source
from .netkeiba import build_netkeiba_source
from .registry import registry
from .netkeiba_career import SOURCE as NETKEIBA_CAREER_SOURCE, fetch_verified_career
from .registry import DataSource, SourceCapabilities


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
            or ""
        ).strip()
        date = str(race.get("date") or "")
        if not cname or not date:
            return {}
        runs = profile_runs(cname, date, int(limit or 5))
        runs = runs or []
        return {"recentRaces": runs[:5], "allPastRuns": runs} if int(limit or 5) > 5 else {"recentRaces": runs}

    return fetch


def _jra_pedigree_adapter(namespace: dict[str, Any]):
    """Reuse the existing JRA horse-profile URL and cache; no new feed."""
    request = _pick(namespace, "_jra_request")
    if request is None:
        return None
    from arvexq.ingest.jra_profile_pedigree import parse_jra_profile_pedigree

    def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        if str(race.get("circuit") or "") not in ("中央", "JRA"):
            return {}
        cname = str(horse.get("_jraHorseCname") or horse.get("jraHorseCname") or "")
        if not cname.startswith("pw01dud") or not str(race.get("date") or ""):
            return {}
        html = request("https://www.jra.go.jp/JRADB/accessU.html", cname, 86400)
        return parse_jra_profile_pedigree(html)

    return fetch


def _jra_official_prior_result_adapter(namespace: dict[str, Any]):
    """Enrich every recent dated start through the canonical JRA result parser."""
    parse_result = _pick(namespace, "_jra_parse_result")
    profile_runs = _pick(namespace, "_jra_profile_runs")
    resolve = _pick(namespace, "_jra_resolve_prior_results")
    if parse_result is None:
        return None

    import inspect
    strict_result = "strict_errors" in inspect.signature(parse_result).parameters

    def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        import base64
        import math
        import unicodedata
        from arvexq.ingest.full_career import date_key, merge_career
        def clean(value):
            return "".join(unicodedata.normalize("NFKC", str(value or "")).split())
        cutoff = date_key(race.get("date"))
        name = clean(horse.get("name"))
        cname = str(horse.get("_jraHorseCname") or horse.get("jraHorseCname") or "").strip()
        if not cutoff or not name:
            return {}
        prior = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)
        if not prior and cname and profile_runs:
            prior = profile_runs(cname, cutoff, 5) or []
        observed_runs = []
        fetch_errors = []
        for run in prior[:5]:
            at = date_key(run.get("date"))
            if not at or at >= cutoff:
                continue
            # Previously verified starts are preserved; retry only missing proof.
            if run.get("marginEvidence") and run.get("timeBehindWinner") is not None:
                continue
            rid = str(run.get("raceId") or "")
            result = None
            if rid.startswith("jraresult-"):
                encoded = rid[len("jraresult-"):]
                try:
                    result_cname = base64.urlsafe_b64decode(
                        encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
                except (ValueError, UnicodeDecodeError):
                    continue
                try:
                    result = parse_result(result_cname, {"date": at, "track": run.get("track")},
                                          **({"strict_errors": True} if strict_result else {}))
                except Exception as exc:
                    fetch_errors.append({"date": at, "track": run.get("track"), "error": f"{type(exc).__name__}: {exc}"})
                    continue
            elif resolve:
                try:
                    result = resolve(horse, run)
                except Exception as exc:
                    fetch_errors.append({"date": at, "track": run.get("track"), "error": f"{type(exc).__name__}: {exc}"})
                    continue
            if not isinstance(result, dict) or date_key(result.get("date")) != at:
                continue
            if clean(result.get("track")) != clean(run.get("track")):
                continue
            if run.get("raceNumber") and int(result.get("raceNumber") or 0) != int(run["raceNumber"]):
                continue
            if run.get("distance") and int(result.get("distance") or run["distance"]) != int(run["distance"]):
                continue
            finishers = (result.get("result") or {}).get("finishers") or []
            matching = [row for row in finishers if clean(row.get("name")) == name]
            winners = [row for row in finishers if row.get("finish") == 1 and row.get("timeSeconds")]
            if len(matching) != 1 or len(winners) != 1:
                continue
            row, winner = matching[0], winners[0]
            own = row.get("timeSeconds")
            if not own or (run.get("finish") and int(run["finish"]) != int(row.get("finish") or 0)):
                continue
            # Do not attach a different start to the saved horse, even with the same name.
            if run.get("timeSeconds") and abs(float(run["timeSeconds"]) - float(own)) > .11:
                continue
            diff = round(float(own) - float(winner["timeSeconds"]), 2)
            if not math.isfinite(diff) or not 0 <= diff <= 30:
                continue
            observed = dict(run)
            observed["timeBehindWinner"] = diff
            observed["marginEvidenceSource"] = "JRA official linked prior result"
            observed["marginEvidence"] = {
                "horseName": row["name"], "date": at, "track": result["track"],
                "raceNumber": result.get("raceNumber"), "resultCname": result.get("resultCname"),
                "winnerName": winner["name"], "winnerTimeSeconds": winner["timeSeconds"],
                "horseTimeSeconds": own, "timeBehindWinner": diff,
            }
            if result.get("resultCname"):
                observed["raceId"] = "jraresult-" + base64.urlsafe_b64encode(
                    result["resultCname"].encode()).decode().rstrip("=")
                observed["raceNumber"] = result.get("raceNumber")
            if row.get("marginText"):
                observed["marginText"] = row["marginText"]
            late = row.get("last3FSeconds")
            if late is not None and 15 <= float(late) <= 90:
                observed["last3fSeconds"] = float(late)
            if row.get("last3FRank") is not None:
                observed["last3fRank"] = row["last3FRank"]
            corners = row.get("cornerPositions")
            if isinstance(corners, list) and corners:
                observed["cornerPositions"] = corners
            observed_runs.append(observed)
        output = {"recentRaces": observed_runs, "allPastRuns": observed_runs} if observed_runs else {}
        if fetch_errors:
            output["historyFetchErrors"] = fetch_errors
        return output

    return fetch


def _nar_store_adapters(namespace: dict[str, Any]):
    store_cls = namespace.get("NarStore")
    if not callable(store_cls):
        return None, None
    # Synchronous providers are called through asyncio.to_thread from several
    # race and horse workers. A shared sqlite3.Connection is bound to its
    # creator thread and fails on any later worker (ProgrammingError).
    # Keep each worker's NarStore private; never disable SQLite thread checks.
    holder = local()

    def store():
        value = getattr(holder, "value", None)
        if value is None:
            value = store_cls()
            holder.value = value
        return value

    def history(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        name = str(horse.get("name") or "").strip()
        date = str(race.get("date") or "")
        if not name or not date:
            return {}
        db = store()
        runs = db.recent_races(name, date, int(limit or 5))
        return {
            "recentRaces": runs[:5],
            "allPastRuns": runs if int(limit or 5) > 5 else [],
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


def _nar_official_past_result_adapter(namespace: dict[str, Any]):
    """Fetch one *prior* NAR race from official results, never the target race."""
    getter = _pick(namespace, "_nar_official_result_fast")
    if getter is None:
        return None

    def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        from arvexq.ingest.full_career import date_key, merge_career
        target = date_key(race.get("date"))
        if not target:
            return {}
        known_name = str(horse.get("name") or "").strip()
        known_runs = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), target)
        fallback_sectional = None
        # The newest official race can have no times/row yet. Try the next
        # recorded starts within the same verified five-run window, not only
        # the very first row. No additional data provider is introduced.
        for run in known_runs[:max(1, min(5, int(limit or 5)))]:
            if not isinstance(run, dict):
                continue
            at = date_key(run.get("date") or run.get("raceDate"))
            track = str(run.get("track") or "").strip()
            no = int(run.get("raceNumber") or run.get("raceNo") or 0)
            if not at or at >= target or not track or not 1 <= no <= 12:
                continue
            if (run.get("last3fSeconds") not in (None, "", 0)
                    and any(run.get(k) not in (None, "")
                            for k in ("marginSeconds", "timeBehindWinner"))):
                continue
            previous = {"date": at, "track": track, "raceNumber": no,
                        "horses": [{"name": known_name,
                                    "horseNumber": run.get("horseNumber") or 0}]}
            found = getter(previous)
            if not isinstance(found, dict):
                continue
            finishers = found.get("finishers") or []
            print("NAR_OFFICIAL_PRIOR_SOURCE", at, track, no,
                  "rows=", len(finishers),
                  "withTime=", sum(bool(f.get("timeSeconds")) for f in finishers),
                  "withMargin=", sum(bool(f.get("marginText")) for f in finishers),
                  "with3F=", sum(bool(f.get("last3FSeconds")) for f in finishers))

            matched = [f for f in finishers if
                       str(f.get("name") or "").strip() == known_name]
            if len(matched) != 1:
                continue
            row = matched[0]
            observed = dict(run)
            observed["date"], observed["track"], observed["raceNumber"] = at, track, no
            official_finish = row.get("finish")
            if (observed.get("finish") in (None, "", 0, "0")
                    and type(official_finish) is int
                    and 1 <= official_finish <= len(finishers)):
                observed["finish"] = official_finish
                observed["researchOfficialPriorFinishVerified"] = True
            seconds = row.get("last3FSeconds")
            if seconds is not None and 15 <= float(seconds) <= 90:
                observed["last3f"] = float(seconds)
                observed["last3fSeconds"] = float(seconds)
            if row.get("marginText") not in (None, ""):
                observed["marginText"] = row["marginText"]
            winner = next((x.get("timeSeconds") for x in finishers
                           if x.get("finish") == 1 and x.get("timeSeconds")), None)
            own = row.get("timeSeconds")
            if winner and own and 0 <= float(own) - float(winner) <= 30:
                observed["timeBehindWinner"] = round(float(own) - float(winner), 2)
            print("NAR_OFFICIAL_PRIOR_MATCH", at, track, no,
                  "winnerTime=", winner, "horseTime=", own,
                  "gap=", observed.get("timeBehindWinner"),
                  "3F=", observed.get("last3fSeconds"),
                  "marginText=", bool(observed.get("marginText")))
            if (observed.get("researchOfficialPriorFinishVerified") is True
                    or observed.get("timeBehindWinner") not in (None, "")
                    or observed.get("marginSeconds") not in (None, "")):
                observed["source"] = "NAR official historical results"
                return {"recentRaces": [observed], "allPastRuns": [observed]}
            if (fallback_sectional is None
                    and any(observed.get(key) not in (None, "")
                            for key in ("last3fSeconds", "marginText"))):
                fallback_sectional = observed
        if fallback_sectional is not None:
            fallback_sectional["source"] = "NAR official historical results"
            return {"recentRaces": [fallback_sectional], "allPastRuns": [fallback_sectional]}
        return {}

    return fetch


def _netkeiba_verified_career_adapter(namespace: dict[str, Any]):
    """One identity-verified heavy provider for complete past runs and starts."""
    import os
    if str(os.getenv("ARVEXQ_NETKEIBA_CAREER_TOTALS", "1")).strip().lower() in {"0", "false", "off", "no"}:
        return None
    getter = _pick(namespace, "_netkeiba_get")
    if getter is None:
        return None
    timeout = float(os.getenv("NETKEIBA_CAREER_TOTALS_TIMEOUT_SEC", "6.0"))

    def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5):
        if int(limit or 5) <= 5:
            return {}
        return fetch_verified_career(
            lambda url: getter(url, timeout, 86400), horse, race, int(limit)
        )

    return fetch

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
        pedigree=_jra_pedigree_adapter(namespace),
    )
    if jra.fetchers:
        registry.register(jra)

    jra_prior = _jra_official_prior_result_adapter(namespace)
    if jra_prior is not None:
        registry.register(DataSource(
            name="jra_official_prior_results", circuit="JRA", priority=12,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": jra_prior},
        ))

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

    nar_results = _nar_official_past_result_adapter(namespace)
    if nar_results is not None:
        registry.register(DataSource(
            name="nar_official_past_results", circuit="NAR", priority=12,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": nar_results},
        ))

    netkeiba = build_netkeiba_source(
        odds=_pick(namespace, "_netkeiba_live_win_odds"),
        results=_pick(namespace, "_netkeiba_current_result"),
        track_weather=_pick(namespace, "_netkeiba_race_meta"),
    )
    if netkeiba.fetchers:
        registry.register(netkeiba)

    career_totals = _netkeiba_verified_career_adapter(namespace)
    if career_totals is not None:
        registry.register(DataSource(
            name=NETKEIBA_CAREER_SOURCE, circuit="both", priority=60,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": career_totals},
        ))

    # Use locally supplied official NAR CSV archives when configured.
    from .nar_official_csv import register_nar_official_archive
    try:
        # Reuse the ZIP files already downloaded by NarSync when no explicit
        # official-archive list was provided; do not create a new data route.
        import os
        from pathlib import Path
        configured = os.getenv("ARVEXQ_NAR_OFFICIAL_CSV_ARCHIVES", "").strip()
        archive_dir = namespace.get("ARCHIVE_DIR")
        existing = []
        if not configured and archive_dir is not None:
            folder = Path(archive_dir)
            if folder.is_dir():
                existing = sorted(
                    (p for p in folder.glob("*.zip") if p.is_file() and (p.name.endswith("_race.zip") or p.name == "daily_race.zip")),
                    key=lambda p: p.name,
                )
        register_nar_official_archive(registry, paths=existing if existing else None)
    except (OSError, ValueError, RuntimeError) as exc:
        import logging
        logging.getLogger(__name__).warning("NAR official CSV unavailable: %s", exc)

    return registry.capability_map()
