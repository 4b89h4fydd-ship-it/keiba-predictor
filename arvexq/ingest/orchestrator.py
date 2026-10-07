from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any

from arvexq.databanks.registry import DataBankRegistry, registry


@dataclass(slots=True)
class FetchResult:
    source: str
    domain: str
    ok: bool
    data: Any = None
    error: str | None = None


async def _call(fetcher, *args, **kwargs):
    # Most legacy fetchers are synchronous urllib/HTML parsers. Run them in a
    # worker thread so one slow source cannot serialise every other fallback.
    if inspect.iscoroutinefunction(fetcher):
        return await fetcher(*args, **kwargs)
    value = await asyncio.to_thread(fetcher, *args, **kwargs)
    if inspect.isawaitable(value):
        return await value
    return value


async def fetch_domain(
    domain: str,
    *args,
    circuit: str | None = None,
    bank_registry: DataBankRegistry = registry,
    **kwargs,
) -> list[FetchResult]:
    """Fetch one data domain from all capable sources without one failure killing the rest."""
    providers = bank_registry.providers(domain, circuit=circuit)
    if not providers:
        return []

    async def run(source):
        fetcher = source.fetchers[domain]
        try:
            data = await _call(fetcher, *args, **kwargs)
            return FetchResult(source=source.name, domain=domain, ok=True, data=data)
        except Exception as exc:
            return FetchResult(source=source.name, domain=domain, ok=False, error=f"{type(exc).__name__}: {exc}")

    return list(await asyncio.gather(*(run(source) for source in providers)))


def best_available(results: list[FetchResult]) -> FetchResult | None:
    for result in results:
        if result.ok and result.data not in (None, "", [], {}):
            return result
    return None
