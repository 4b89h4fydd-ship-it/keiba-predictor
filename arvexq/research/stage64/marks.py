"""Research-only independent win/axis roles; no fabricated confidence grade."""
def roles(win, podium, scenario_wins=None):
    if set(win)!=set(podium):
        raise ValueError("role roster mismatch")
    # Favor horses with a viable winning path across the selected pace scenarios.
    # Keep aggregate win probability as the tie-breaker and retain original
    # behavior when only one scenario exists or scenario evidence is absent.
    if scenario_wins and len(scenario_wins) > 1:
        if any(set(row) != set(win) for row in scenario_wins):
            raise ValueError("scenario roster mismatch")
        worst = {no: min(row[no] for row in scenario_wins) for no in win}
        order = sorted(win, key=lambda no: (-worst[no], -win[no], no))
        method = "scenario-robust-win"
    else:
        worst = {}
        order = sorted(win, key=lambda no: (-win[no], no))
        method = "aggregate-win"
    axis=sorted(podium,key=lambda n:(-podium[n],n))
    return {"status":"research-only-unvalidated",
            "winRole":{"horseNumber":order[0],"meaning":"highest-model-win-probability","grade":None},
            "axisRole":{"horseNumber":axis[0],"meaning":"highest-model-top3-probability","grade":None},
            "orderedWinCandidates":order,"orderedAxisCandidates":axis,
            "decisionMethod":method,"scenarioWorstWin":worst,
            "productMarks":None}
