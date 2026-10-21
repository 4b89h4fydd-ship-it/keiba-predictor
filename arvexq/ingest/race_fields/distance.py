"""#16 Official distance independent of surface/going."""
from arvexq.components.item_017.course import extract as extract_course
def extract(text):
    return extract_course(text)[1]
