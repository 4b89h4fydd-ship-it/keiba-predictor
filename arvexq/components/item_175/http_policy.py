"""Existing readback HTTP decisions, no new retries or API endpoints."""

def retryable_readback_status(status):
    return status in (408, 500, 502, 503, 504)


def display_fallback_status(status):
    return status in (404, 503)
