"""Research-only independent win/axis roles; no fabricated confidence grade."""
def roles(win, podium):
    if set(win)!=set(podium):
        raise ValueError("role roster mismatch")
    order=sorted(win,key=lambda n:(-win[n],n))
    axis=sorted(podium,key=lambda n:(-podium[n],n))
    return {"status":"research-only-unvalidated",
            "winRole":{"horseNumber":order[0],"meaning":"highest-model-win-probability","grade":None},
            "axisRole":{"horseNumber":axis[0],"meaning":"highest-model-top3-probability","grade":None},
            "orderedWinCandidates":order,"orderedAxisCandidates":axis,
            "productMarks":None}
