"""Read-only mobile-neutral view DTO; screen markup/CSS remain existing owners.

Separating formatting from saved storage prevents the browser from recalculating
forecast, marks or tickets and prevents retroactive original exposure.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any


def _observation_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    basic_keys = ("name", "jockey", "trainer", "carriedWeight")
    past_keys = ("track", "distance", "finish", "last3f")
    states = ("observed", "missing", "invalid")
    basic = {key: {state: 0 for state in states} for key in basic_keys}
    past = {key: {state: 0 for state in states} for key in past_keys}
    quote = {state: 0 for state in
             ("missing", "invalid", "observed-unverified-timestamp")}
    total = 0
    for row in rows:
        ready = row["readiness"]
        for key in basic_keys:
            basic[key][ready["basicFields"][key]] += 1
        for run in ready["pastFieldStates"]:
            total += 1
            for key in past_keys:
                past[key][run["fields"][key]] += 1
        quote[ready["quoteTimeState"]] += 1
    return {
        "schema": "arvexq-v3-observation-summary-1",
        "runnerRows": len(rows),
        "observedPriorRuns": total,
        "basicFields": basic,
        "pastFields": past,
        "quoteTime": quote,
        "fullCareerVerified": False,
        "marketFreshnessVerified": False,
    }


def factual_screen(response: dict[str, Any], *, recent_limit: int = 5) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("schema") != "arvexq-v3-factual-api-1":
        raise ValueError("v3 factual API response required")
    if isinstance(recent_limit, bool) or not isinstance(recent_limit, int) or not 0 <= recent_limit <= 20:
        raise ValueError("recent_limit must be an integer between zero and twenty")
    entries = response.get("entries")
    history = response.get("history")
    odds = response.get("odds")
    runner_readiness = response.get("runnerReadiness")
    if not isinstance(entries, list) or not isinstance(history, list) or not isinstance(odds, list):
        raise ValueError("incomplete observed response")
    if not isinstance(runner_readiness, list) or not len(entries) == len(history) == len(odds) == len(runner_readiness):
        raise ValueError("runner/history/odds alignment mismatch")
    price_fields = response.get("oddsFields")
    if not isinstance(price_fields, dict):
        raise ValueError("runner readiness oddsFields missing")
    observed_states = {}
    for field in ("win", "place", "popularity"):
        values = price_fields.get(field)
        if not isinstance(values, list) or len(values) != len(entries):
            raise ValueError("runner readiness oddsFields alignment mismatch")
        observed_states[field] = values
    # Preserve source row identity and refuse ambiguous duplicates, not a
    # fabricated index/name merge that could attach another horse's history.
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for h, past, price, readiness in zip(entries, history, odds, runner_readiness):
        number = h.get("horseNumber")
        if isinstance(number, bool):
            raise ValueError("invalid runner number")
        try:
            actual = int(number)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("invalid runner number") from None
        if actual <= 0 or actual in seen or number != past.get("horseNumber") or number != price.get("horseNumber"):
            raise ValueError("runner identity collision/misalignment")
        seen.add(actual)
        if (not isinstance(readiness, dict) or
                readiness.get("schema") != "arvexq-v3-runner-readiness-1" or
                readiness.get("horseNumber") != number or
                readiness.get("observedPriorRunCount") != past.get("observedPriorRunCount")):
            raise ValueError("runner readiness identity/count mismatch")
        for field in ("win", "place", "popularity"):
            fact = observed_states[field][len(seen) - 1]
            if (not isinstance(fact, dict) or fact.get("horseNumber") != number or
                    fact.get("state") != readiness.get(field)):
                raise ValueError("runner readiness market identity/state mismatch")
        # Every published basic-field status must match its saved, allowlisted
        # runner row. Neither source nor official verification is inferred.
        basic = readiness.get("basicFields")
        reasons = readiness.get("basicFieldReasons")
        keys = ("name", "jockey", "trainer", "carriedWeight")
        if not isinstance(basic, dict) or not isinstance(reasons, dict) or (
                set(basic) != set(keys) or set(reasons) != set(keys)):
            raise ValueError("runner readiness basic field contract mismatch")
        for key in keys:
            value = h.get(key)
            reason = ("absent" if key not in h else "null" if value is None
                      else "placeholder" if isinstance(value, str) and
                      value.strip() in ("", "-", "--", "不明")
                      else "invalid-type-or-number" if isinstance(value, bool) or
                      isinstance(value, float) and not isfinite(value)
                      else "saved-value")
            state = ("missing" if reason in ("absent", "null", "placeholder")
                     else "invalid" if reason == "invalid-type-or-number"
                     else "observed")
            if basic[key] != state or reasons[key] != reason:
                raise ValueError("runner readiness basic field evidence mismatch")
        expected_history = ("partial-unverified" if past["observedPriorRunCount"] > 0
                            else "missing")
        expected_odds = ("observed-unverified" if
                         readiness.get("win") == readiness.get("place") == "observed"
                         else "incomplete")
        if (readiness.get("history") != expected_history or
                readiness.get("odds") != expected_odds or
                readiness.get("canClaimFullyRetrieved") is not False or
                readiness.get("marketFreshnessVerified") is not False or
                readiness.get("allCareerRunsVerified") is not False):
            raise ValueError("runner readiness observation state mismatch")
        runs = past.get("pastRuns")
        if not isinstance(runs, list):
            raise ValueError("past run list missing")
        observed_run_count = past.get("observedPriorRunCount")
        if type(observed_run_count) is not int or observed_run_count != len(runs):
            raise ValueError("runner readiness historical run count mismatch")
        states = readiness.get("pastFieldStates")
        if not isinstance(states, list) or len(states) != len(runs):
            raise ValueError("runner readiness past field alignment mismatch")
        for run, item in zip(runs, states):
            if not isinstance(run, dict) or not isinstance(item, dict) or item.get("date") != run.get("date"):
                raise ValueError("runner readiness past field identity mismatch")
            cell_states = item.get("fields")
            keys = ("track", "distance", "finish", "last3f")
            if not isinstance(cell_states, dict) or set(cell_states) != set(keys):
                raise ValueError("runner readiness past field contract mismatch")
            for key in keys:
                value = run.get(key)
                actual_state = ("missing" if value is None or isinstance(value, str) and
                                value.strip() in ("", "-", "--", "不明") else
                                "invalid" if isinstance(value, bool) or isinstance(value, float)
                                and not isfinite(value) else "observed")
                if cell_states[key] != actual_state:
                    raise ValueError("runner readiness past field state mismatch")
        # Saved odds timestamps are not exposed in the allowlisted runner
        # row. The independent quoteFields contract is responsible for
        # timestamp provenance; this view only validates a constrained state.
        if readiness.get("quoteTimeState") not in (
                "missing", "invalid", "observed-unverified-timestamp"):
            raise ValueError("runner readiness quote time state mismatch")
        rows.append({
            "horseNumber": actual,
            "horse": deepcopy(h),
            "odds": deepcopy({k: v for k, v in price.items() if k != "horseNumber"}),
            "recentRaces": deepcopy(runs[:recent_limit]),
            "observedPriorRunCount": past["observedPriorRunCount"],
            "careerCompleteness": "unverified",
            "readiness": deepcopy(readiness),
        })
    # Validate independent coverage totals against the original per-runner
    # evidence rather than accepting potentially inflated coverage metadata.
    coverage = response.get("coverage")
    counts = coverage.get("counts") if isinstance(coverage, dict) else None
    if not isinstance(counts, dict):
        raise ValueError("runner observation coverage counts missing")
    expected_counts = {
        "runnerRows": len(rows),
        "observedPriorRuns": sum(row["observedPriorRunCount"] for row in rows),
        "runnersWithPriorRuns": sum(row["observedPriorRunCount"] > 0 for row in rows),
        "oddsHorseRows": sum(
            any(key in price and price[key] is not None
                for key in ("winOdds", "placeOdds", "popularity"))
            for price in odds),
    }
    for key, value in expected_counts.items():
        if type(counts.get(key)) is not int or counts[key] != value:
            raise ValueError("runner observation coverage total mismatch")
    market_counts = price_fields.get("counts")
    if not isinstance(market_counts, dict):
        raise ValueError("runner observation market counts missing")
    for field, facts in observed_states.items():
        actual = {state: sum(fact["state"] == state for fact in facts)
                  for state in ("observed", "missing", "invalid")}
        recorded = market_counts.get(field)
        if not isinstance(recorded, dict) or recorded != actual:
            raise ValueError("runner observation market total mismatch")
    rows.sort(key=lambda row: row["horseNumber"])
    race = response.get("race") or {}
    expected = race.get("fieldSize") if isinstance(race, dict) else None
    roster = ("count-mismatch" if type(expected) is int and expected > 0
              and expected != len(rows) else "unverified")
    observed_runs = sum(row["observedPriorRunCount"] for row in rows)
    history_state = "missing" if observed_runs == 0 else "partial-unverified"
    odds_state = ("observed-unverified" if rows and
                  all(row["readiness"]["odds"] == "observed-unverified" for row in rows)
                  else "incomplete")
    readiness = {
        "schema": "arvexq-v3-display-readiness-1",
        "complete": False,
        "roster": roster,
        "history": history_state,
        "odds": odds_state,
        "message": "保存済み観測データのみ。全項目の取得完了は未確認",
        "canClaimFullyRetrieved": False,
        "predictionsEnabled": False,
    }
    return {
        "schema": "arvexq-v3-factual-screen-1",
        "race": deepcopy(response.get("race")),
        "rows": rows,
        "results": deepcopy(response.get("results")) if response.get("resultsIncluded") else None,
        "resultFields": deepcopy(response.get("resultFields")) if response.get("resultsIncluded") else None,
        "coverage": deepcopy(response.get("coverage")),
        "oddsFields": deepcopy(response.get("oddsFields")),
        "quoteFields": deepcopy(response.get("quoteFields")),
        "displayReadiness": readiness,
        "observationSummary": _observation_summary(rows),
        "predictionStatus": "not-implemented",
        "marks": None,
        "tickets": None,
    }
