"""NAR corner passage-order parsing, independent of application and forecasts."""
from __future__ import annotations
import re
from arvexq.components.item_040.field_normalization import _clean

def _top_level_tokens(text: str) -> list[str]:
    text = _clean(text)
    if not text:
        return []
    tokens: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            if buf:
                tokens.append("".join(buf).strip())
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf).strip())
    return tokens

def parse_corner_order(text: str) -> dict[int, int]:
    positions: dict[int, int] = {}
    rank = 1
    for token in _top_level_tokens(text):
        tied = token.startswith("(") and token.endswith(")")
        nums = [int(x) for x in re.findall(r"\d+", token)]
        if not nums:
            continue
        if tied and len(nums) > 1:
            for horse_no in nums:
                positions[horse_no] = rank
            rank += len(nums)
        else:
            for horse_no in nums:
                positions[horse_no] = rank
                rank += 1
    return positions
