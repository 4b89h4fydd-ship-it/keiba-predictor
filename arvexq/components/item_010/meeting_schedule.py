"""Independent JRA meeting-day identification from published calendar headings.

Return observed (meeting number, venue, meeting day). Unknowns remain empty.
"""
import re

MEETING_DAY_RE = re.compile(r"(\d+)回\s*([^\s\d]+?)\s*(\d+)日目")


def extract(table, meeting_day_pattern=MEETING_DAY_RE, text_of=None):
    """Extract the meeting calendar heading adjacent to an official race table."""
    if text_of is None:
        text_of = lambda node: re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""
    previous = table.find_previous(string=meeting_day_pattern)
    if previous is not None:
        match = meeting_day_pattern.search(str(previous))
        if match:
            return int(match.group(1)), match.group(2), int(match.group(3))
    node = table.find_previous(["h2", "h3", "h4", "h5", "strong", "p", "div"])
    attempts = 0
    while node is not None and attempts < 30:
        match = meeting_day_pattern.search(text_of(node))
        if match:
            return int(match.group(1)), match.group(2), int(match.group(3))
        node = node.find_previous(["h2", "h3", "h4", "h5", "strong", "p", "div"])
        attempts += 1
    return 0, "", 0
