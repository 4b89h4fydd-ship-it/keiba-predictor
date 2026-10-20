"""Offline NAR ablations with no production imports or external requests."""
from .ability import prior_runs, score_field
from .running_style import style_field
from .pace import adjustments
from .probability import distribution
from .tickets import top10
from .marks import run as marks

ARMS = {
    "baseline": ("baseline", None, "four", 1.),
    "recent5": ("recent5", None, "four", 1.),
    "recent5_shrunk": ("recent5_shrunk", None, "four", 1.),
    "style_recent5": ("baseline", 5, "four", 1.),
    "pace_neutral": ("baseline", None, "neutral", 1.),
    "temperature_half": ("baseline", None, "four", .5),
    "temperature_two": ("baseline", None, "four", 2.),
}


def predict(race, arm="baseline"):
    # JRA execution intentionally blocked until a separately reviewed connection.
    if race.get("circuit") not in ("地方","nar") or not race["id"].startswith("nar-"+race["date"]+"-"):
        raise ValueError("NAR-only experiment; circuit/date mismatch")
    active = [h for h in race["horses"] if not any(
        h.get(k) for k in ("scratched","withdrawn","cancelled"))]
    numbers = [h.get("horseNumber") for h in active]
    if any(type(n) is not int or n <= 0 for n in numbers) or len(set(numbers)) != len(numbers) or len(numbers)<3:
        raise ValueError("invalid roster")
    # Stored fieldSize refers to the full saved roster, including withdrawals.
    if type(race.get("fieldSize")) is not int or race["fieldSize"]!=len(race["horses"]):
        raise ValueError("saved field size mismatch")
    histories = {h["horseNumber"]:prior_runs(h,race["date"]) for h in active}
    method, window, mode, temperature = ARMS[arm]
    ability = score_field(histories,method)
    styles = style_field(histories,window)
    missing_ability = [no for no,v in ability.items() if v is None]
    missing_style = [no for no,v in styles.items() if v is None]
    if missing_ability or missing_style:
        return {"status":"incomplete-evidence", "missingAbility":missing_ability,
                "missingStyle":missing_style, "probabilities":None,
                "marks":None,"tickets":None}
    deltas = adjustments(styles,mode)
    probs = distribution(ability,deltas,temperature)
    return {"status":"research-only", "ability":ability, "runningStyle":styles,
            "pace":deltas, "probabilities":probs["win"],
            "trifectaMass":sum(probs["trifecta"].values()),
            "marks":marks()["marks"], "tickets":top10(probs),
            "calibrationVerified":False}
