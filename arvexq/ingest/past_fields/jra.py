"""Compose provider-specific, field-independent historical observations.

This adapter does not calculate forecasts or persist sources. Individual fields
may be replaced and unit-tested without reimplementing the race-card parser.
"""
import re
from arvexq.components.item_042.date import extract_date
from arvexq.components.item_043.track import extract_track
from arvexq.components.item_044.distance import extract_distance, extract_surface
from arvexq.components.item_045.going import extract_going
from arvexq.components.item_047.finish import extract_finish
from arvexq.components.item_048.clock import extract_time_seconds
from arvexq.components.item_049.margin import extract_margin_seconds
from arvexq.components.item_050.corners import extract_corners
from arvexq.components.item_052.carried_weight import extract_carried_weight
from arvexq.components.item_054.field_size import extract_field_size
from arvexq.components.item_053.jockey import extract_jockey
from arvexq.components.item_051.last3f import extract_last3f_seconds
from arvexq.components.item_046.grade import extract_class

def parse_jra_history_cell(cell, cutoff, tracks, race_id=""):
    text=re.sub(r"\s+"," ",cell.get_text(" ",strip=True)).strip()
    date=extract_date(text)
    if not date or (cutoff and date>=cutoff):return None
    track=extract_track(text,tracks)
    finish=extract_finish(text)
    title=""
    if track:
        after=text.split(track,1)[1].strip()
        after=re.split(r"\s+(?:\d{1,2}着|\d{1,2}頭|\d+番)",after,1)[0]
        title=after[:60].strip()
    row={
        "date":date,"track":track,"title":title,
        "distance":extract_distance(text),"surface":extract_surface(text),
        "condition":extract_going(text),"weather":"不明",
        "fieldSize":extract_field_size(text),"finish":finish,
        "timeSeconds":extract_time_seconds(text),
        "marginSeconds":extract_margin_seconds(text,finish),
        "cornerPositions":extract_corners(cell),
        "carriedWeight":extract_carried_weight(text),
        "raceId":race_id,"source":"JRA公式"
    }
    grade=extract_class(text)
    jockey=extract_jockey(text)
    last3f=extract_last3f_seconds(text)
    if grade:row["class"]=grade
    if jockey:row["jockey"]=jockey
    if last3f is not None:row["last3FSeconds"]=last3f
    return row
