"""Fail-closed audit of pre-off feature provenance. No prediction code changes."""
from datetime import datetime, timezone


def audit_feature_provenance(race, features):
    """Return violations; missing provenance is not evidence of pre-off availability."""
    errors = []
    post = race.get("scheduledPostEpoch")
    try:
        post = int(post)
    except (TypeError, ValueError):
        return ["missing-scheduled-post"]
    for index, item in enumerate(features):
        if not isinstance(item, dict):
            errors.append(f"{index}:invalid-feature")
            continue
        captured = item.get("availableAtEpoch")
        try:
            captured = int(captured)
        except (TypeError, ValueError):
            errors.append(f"{index}:missing-availability-time")
            continue
        if captured >= post:
            errors.append(f"{index}:post-off-information")
        if item.get("sourceRaceId") == race.get("id"):
            errors.append(f"{index}:target-race-leakage")
        if item.get("isResultDerived") is True:
            errors.append(f"{index}:result-derived-feature")
    return errors
