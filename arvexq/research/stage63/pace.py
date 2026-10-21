"""Fixed tactical hypotheses, not estimated scenario occurrence frequencies."""
def adjustments(styles, mode="four"):
    if mode not in ("four", "neutral"):
        raise ValueError("unknown pace mode")
    if any(v is None for v in styles.values()):
        return None
    pressure = sum(v[0]+.5*v[1] for v in styles.values())
    neutral = {no:0. for no in styles}
    if mode == "neutral":
        return [neutral]
    return [neutral,
            {no:.1*(s+c-e)*min(2.,pressure)/2 for no,(e,f,s,c) in styles.items()},
            {no:.1*(e+.4*f-.5*c) for no,(e,f,s,c) in styles.items()},
            {no:.1*(s+c-.5*e) for no,(e,f,s,c) in styles.items()}]
