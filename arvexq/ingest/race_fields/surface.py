"""#15 Course surface independently observed, never inferred from going."""
from .course import extract as extract_course
def extract(text):
    desc=extract_course(text)[0]
    return "芝" if "芝" in desc else ("ダート" if "ダート" in desc else ("障害" if "障" in desc else ""))
