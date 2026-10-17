"""#16 Official distance independent of surface/going."""
from .course import extract as extract_course
def extract(text):
    return extract_course(text)[1]
