"""Research-only mark-first betting and outcome verification.

Ticket templates are explicit diagnostic rules, not calibrated probabilities.
"""
from itertools import combinations, permutations

MARKS=("◎","○","▲","△","☆","注")
KINDS=("単勝","複勝","馬連","ワイド","馬単","3連複","3連単")

def assign_marks(ranking):
    return {mark:ranking[i] for i,mark in enumerate(MARKS) if len(ranking)>i}

def tickets_from_marks(marks):
    values=list(marks.values())
    if len(values)<3: return {k:[] for k in KINDS}
    a,b,c=values[:3]
    support=values[3:6]
    pairs=[tuple(sorted(p)) for p in combinations(values[:5],2)]
    triples=[tuple(sorted(p)) for p in combinations(values[:5],3)]
    return {
        "単勝":[(a,)],
        "複勝":[(a,),(b,)],
        "馬連":pairs[:10],
        "ワイド":pairs[:10],
        "馬単":list(permutations(values[:4],2))[:10],
        "3連複":triples[:10],
        "3連単":list(permutations(values[:4],3))[:10],
    }

def check_hits(tickets,finish):
    if len(finish)<3: return {}
    first,second,third=finish[:3]
    top3={first,second,third}
    return {
        "単勝":lambda t:t[0]==first,
        "複勝":lambda t:t[0] in top3,
        "馬連":lambda t:set(t)=={first,second},
        "ワイド":lambda t:set(t).issubset(top3),
        "馬単":lambda t:t==(first,second),
        "3連複":lambda t:set(t)==top3,
        "3連単":lambda t:t==(first,second,third),
    }
