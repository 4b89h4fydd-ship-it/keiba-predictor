"""Independent research selection; no stake advice or expected-return claim."""
def top10(probabilities):
    joint = probabilities["trifecta"]
    return sorted(joint, key=lambda combo:(-joint[combo],combo))[:10]


def run(*, probabilities):
    return {"status":"research-only-not-a-recommendation",
            "combos":top10(probabilities)}
