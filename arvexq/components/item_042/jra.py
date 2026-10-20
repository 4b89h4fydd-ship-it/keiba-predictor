"""Compose provider-specific, field-independent historical observations.

This adapter does not calculate forecasts or persist sources. Individual fields
may be replaced and unit-tested without reimplementing the race-card parser.
"""
import re
from arvexq.ingest.past_fields.date import extract_date
from arvexq.ingest.past_fields.track import extract_track
from arvexq.ingest.past_fields.distance import extract_distance, extract_surface
from arvexq.ingest.past_fields.going import extract_going
from arvexq.ingest.past_fields.finish import extract_finish
from arvexq.ingest.past_fields.clock import extract_time_seconds
from arvexq.ingest.past_fields.margin import extract_margin_seconds
from arvexq.ingest.past_fields.corners import extract_corners
from arvexq.ingest.past_fields.carried_weight import extract_carried_weight
from arvexq.ingest.past_fields.field_size import extract_field_size
from arvexq.ingest.past_fields.jockey import extract_jockey
from arvexq.ingest.past_fields.last3f import extract_last3f_seconds
from arvexq.ingest.past_fields.grade import extract_class

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
