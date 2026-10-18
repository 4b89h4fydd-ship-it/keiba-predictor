"""Bounded HTTP readiness checks for an already launched runtime."""
from __future__ import annotations

import os
import time
import urllib.request
from typing import Callable


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def probe_health(url: str, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise OSError("runtime health HTTP " + str(response.status))


def wait_ready(url: str, *, pid: int, timeout: float = 60,
               interval: float = 1, request_timeout: float = 2,
               probe: Callable = probe_health, alive: Callable = process_alive,
               clock: Callable = time.monotonic, sleeper: Callable = time.sleep) -> int:
    """Return probe count on readiness; stop at process death or the deadline."""
    if timeout <= 0 or interval <= 0 or request_timeout <= 0 or pid <= 0:
        raise ValueError("positive PID, deadline, interval and request timeout required")
    deadline = clock() + timeout
    attempts = 0
    last_error = None
    while True:
        if not alive(pid):
            raise RuntimeError("runtime process exited before readiness")
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("runtime readiness deadline exceeded") from last_error
        attempts += 1
        try:
            probe(url, min(request_timeout, remaining))
            return attempts
        except OSError as exc:
            last_error = exc
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("runtime readiness deadline exceeded") from last_error
        sleeper(min(interval, remaining))
