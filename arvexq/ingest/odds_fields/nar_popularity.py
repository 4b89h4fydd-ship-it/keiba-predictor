"""NAR official observed win-odds popularity, independent of odds extraction.

Preserves the existing competition ranking: ties share the earliest rank.
No ranking is inferred when the official win odds have not been observed.
"""


def apply_observed_win_popularity(out: dict) -> dict:
    ranked = sorted((float(v["winOdds"]), no) for no, v in out.items() if v.get("winOdds"))
    rank = 0
    last = None
    for ix, (odd, no) in enumerate(ranked, 1):
        if last is None or odd != last:
            rank = ix
        out[no]["popularity"] = rank
        last = odd
    return out
