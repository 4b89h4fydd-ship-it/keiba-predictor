"""Research-only feature challengers. Never retroactively claim pre-off validation."""
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.reliability_candidate import score as reliability_score


def candidates(horse, race):
    runs = observed_runs(horse, race, limit=5)
    base = reliability_score(horse, race)
    if base is None:
        return {}
    distance = race.get("distance")
    track = race.get("track")
    surface = race.get("surface")
    opponent = []
    course = []
    for run in runs:
        q = (run["fieldSize"] - run["finish"]) / (run["fieldSize"] - 1)
        level = run.get("opponentLevel")
        if isinstance(level, (int, float)) and 0 <= level <= 1:
            opponent.append(q * (0.5 + 0.5 * level))
        if (distance and run.get("distance") and abs(float(run["distance"]) - float(distance)) <= 150
                and track and run.get("track") == track and surface and run.get("surface") == surface):
            course.append(q)
    out = {"reliability": base}
    if opponent:
        out["opponent"] = 0.8 * base + 0.2 * sum(opponent) / len(opponent)
    if course:
        out["course"] = 0.8 * base + 0.2 * sum(course) / len(course)
    return out
