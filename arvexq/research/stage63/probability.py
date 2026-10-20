"""Stable Plackett-Luce mixtures. Numerical normalization is not calibration."""
import itertools
import math


def distribution(ability, deltas, temperature=1.):
    if type(temperature) not in (int,float) or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("invalid temperature")
    if len(ability) < 3 or not deltas or any(v is None for v in ability.values()):
        raise ValueError("incomplete ability/scenarios")
    joint = {combo:0. for combo in itertools.permutations(sorted(ability), 3)}
    win = {no:0. for no in ability}
    for delta in deltas:
        if set(delta) != set(ability):
            raise ValueError("scenario roster mismatch")
        logits = {no:(v+delta[no])/temperature for no,v in ability.items()}
        if any(not math.isfinite(v) for v in logits.values()):
            raise ValueError("nonfinite score")
        # Normalize afresh after each removal; avoid subtracting near-one floats.
        def softmax(remaining):
            peak = max(logits[i] for i in remaining)
            weights = {i:math.exp(logits[i]-peak) for i in remaining}
            total = sum(weights.values())
            return {i:w/total for i,w in weights.items()}
        first = softmax(logits)
        for a,pa in first.items():
            win[a] += pa/len(deltas)
            second = softmax([i for i in logits if i != a])
            for b,pb in second.items():
                third = softmax([i for i in logits if i not in (a,b)])
                for c,pc in third.items():
                    joint[a,b,c] += pa*pb*pc/len(deltas)
    return {"win":win, "trifecta":joint, "calibrationVerified":False}
