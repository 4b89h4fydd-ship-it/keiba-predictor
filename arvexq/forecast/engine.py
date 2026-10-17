"""112: Production prediction interface; no unapproved model or fallback."""
VERSION = 'arvexq-prediction-removed'

def build_prediction(facts):
    """Fact DTO -> None while no prediction model is approved. No side effects."""
    return None
