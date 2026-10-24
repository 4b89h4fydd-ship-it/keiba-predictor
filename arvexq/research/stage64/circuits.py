"""Separately registered circuit baselines, with no fitted weight transfer."""
CONFIGS = {
    "jra": {"version":"jra-flat-shadow-v1","pace":"neutral",
            "ability":"baseline","temperature":1.0,"styleWindow":None},
    "nar": {"version":"nar-flat-shadow-v2-observed-career","pace":"four",
            "ability":"baseline","temperature":1.0,"styleWindow":None},
}


def circuit(race):
    aliases={"中央":"jra","地方":"nar","jra":"jra","nar":"nar"}
    value=aliases.get(race.get("circuit"))
    if value is None or not race.get("id","").startswith(value+"-"+race.get("date","")+"-"):
        raise ValueError("race identity/circuit/date conflict")
    return value


def discipline(row):
    if row.get("track")=="帯広ば" or row.get("surface")=="ばんえい" or row.get("analysisMode")=="ばんえい":
        return "banei"
    if row.get("surface")=="障害" or row.get("analysisMode")=="障害":
        return "jumps"
    return "flat"


def active(horse):
    return not (any(horse.get(k) for k in ("scratched","withdrawn","cancelled")) or
                str(horse.get("status") or "").strip() in
                ("出走取消","競走除外","取消","除外","scratched","withdrawn"))
