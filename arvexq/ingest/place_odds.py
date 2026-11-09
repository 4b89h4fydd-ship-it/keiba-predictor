"""Requirement #60: Independent observed place-odds lower/upper extraction.

Do not infer missing returns from win odds, popularity or other races.
"""
import re

def place_odds(value):
    s=str(value or "").strip().replace("，",",")
    match=re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:[-～〜~]\s*(\d+(?:\.\d+)?))?\s*",s)
    if not match:return None
    low=float(match.group(1))
    high=float(match.group(2)) if match.group(2) is not None else low
    if low<=0 or high<low:return None
    return {"placeOddsLow":low,"placeOddsHigh":high}

def place_odds_pair(low,high):
    # The official NAR page renders the range across two cells and the
    # range separator travels with the low cell ("3.5-" | "7.8"), which
    # place_odds alone must keep rejecting as an incomplete single
    # value. Strip a dangling separator from either side here, where
    # the two observed bounds are both present.
    a=place_odds(re.sub(r"[-～〜~]\s*$","",str(low or "").strip()))
    b=place_odds(re.sub(r"^\s*[-～〜~]","",str(high or "").strip()))
    if not a or not b:return None
    lo=a["placeOddsLow"];hi=b["placeOddsHigh"]
    return {"placeOddsLow":lo,"placeOddsHigh":hi} if hi>=lo else None
