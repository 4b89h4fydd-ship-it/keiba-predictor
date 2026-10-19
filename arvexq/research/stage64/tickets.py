"""Hypothetical fixed-count comparison; product recommendations stay withheld."""
from arvexq.research.stage63.tickets import top10


def select(probabilities):
    combos=top10(probabilities)
    return {"status":"research-only-unvalidated","hypotheticalTrifectaTop10":combos,
            "estimatedMassUncalibrated":sum(probabilities["trifecta"][c] for c in combos),
            "recommendedBets":None,
            "blocker":"No independent calibration or preoff ticket-price/utility validation"}
