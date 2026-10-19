"""Bounded HTTP retries for existing D1 readback; no extra acquisition endpoint."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

MAX_RESPONSE_BYTES = 32 * 1024 * 1024

def get_json(url, *, timeout=20, attempts=2, opener=urllib.request.urlopen,
             sleeper=time.sleep):
    """Bounded GET retries; invalid JSON and schema are not successful reads."""
    if timeout <= 0 or attempts < 1:
        raise ValueError("positive HTTP timeout and attempt count required")
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={
                "accept": "application/json", "user-agent": "ARVEXQ-FactReadback/1"})
            with opener(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("D1 JSON response exceeds read budget")
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, dict):
                raise ValueError("D1 JSON response must be an object")
            return result
        except urllib.error.HTTPError as exc:
            # Honor server 429 immediately: retrying can deepen throttling.
            if exc.code == 429 or exc.code not in (408, 500, 502, 503, 504) or attempt + 1 == attempts:
                raise
        except OSError:
            if attempt + 1 == attempts:
                raise
        sleeper(min(2, 0.5 * (attempt + 1)))
