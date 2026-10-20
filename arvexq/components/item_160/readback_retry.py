"""Bounded HTTP retries for existing D1 readback; no extra acquisition endpoint."""
from __future__ import annotations

import json
import http.client
import time
import urllib.error
import urllib.request
from arvexq.components.item_175.http_policy import retryable_readback_status

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
                chunks = []
                total = 0
                # read(n) may return a short chunk before EOF. A single read
                # can truncate chunked edge responses; consume the SAME
                # response to EOF within the same existing byte cap.
                while total <= MAX_RESPONSE_BYTES:
                    chunk = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                raw = b''.join(chunks)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("D1 JSON response exceeds read budget")
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, dict):
                raise ValueError("D1 JSON response must be an object")
            return result
        except urllib.error.HTTPError as exc:
            # Honor server 429 immediately: retrying can deepen throttling.
            if exc.code == 429 or not retryable_readback_status(exc.code) or attempt + 1 == attempts:
                raise
        except (json.JSONDecodeError, UnicodeDecodeError, http.client.IncompleteRead):
            # A 200 response can be cut mid-transfer by the edge. Retry the
            # SAME URL within the existing attempt budget; never accept a
            # partial body or substitute another race/view as a successful read.
            if attempt + 1 == attempts:
                raise
        except OSError:
            if attempt + 1 == attempts:
                raise
        sleeper(min(2, 0.5 * (attempt + 1)))
