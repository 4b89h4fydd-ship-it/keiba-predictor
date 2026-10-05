from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("ARVEXQ_APP_NAME", "ARVEXQ")
    cache_version: str = os.getenv("ARVEXQ_CACHE_VERSION", "v1")
    prediction_version: str = os.getenv("ARVEXQ_PREDICTION_VERSION", "v1")
    request_timeout_seconds: float = float(os.getenv("ARVEXQ_REQUEST_TIMEOUT", "8"))
    max_parallel_fetches: int = int(os.getenv("ARVEXQ_MAX_PARALLEL_FETCHES", "8"))


settings = Settings()
