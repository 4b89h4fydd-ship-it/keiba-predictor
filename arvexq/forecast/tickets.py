"""Return only empirically fused, sealed pre-off ticket selections."""


def generate_tickets(prediction, marks, quoted_odds=None, min_hit_probability=0.8,
                     place_payout_slots=3, race=None):
    from arvexq.prediction.empirical_fusion import VERSION as FUSION_VERSION
    if not isinstance(prediction, dict) or prediction.get("modelVersion") != FUSION_VERSION:
        return []
    if prediction.get("predictionStatus") != "ready":
        return []
    sealed = prediction.get("recommendedBets")
    if not isinstance(sealed, list) or sum(len(t.get("combos") or [])
            for t in sealed if isinstance(t, dict)) > 5:
        return []
    return [dict(t, combos=[list(c) for c in t["combos"]])
            for t in sealed if isinstance(t, dict) and
            t.get("kind") in ("馬連", "ワイド", "馬単", "3連複", "3連単")
            and isinstance(t.get("combos"), list)]
