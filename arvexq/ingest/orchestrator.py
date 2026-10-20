from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any

from arvexq.components.item_041.registry import DataBankRegistry, registry


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
    only_sources: set[str] | None = None,
    **kwargs,
) -> list[FetchResult]:
    """Fetch from all capable sources or a targeted group, isolating failures."""
    providers = bank_registry.providers(domain, circuit=circuit)
    if only_sources is not None:
        providers = [p for p in providers if p.name in only_sources]
    if not providers:
        return []

    async def run(source):
        fetcher = source.fetchers[domain]
        # Retry only transient failures through the SAME registered provider.
        # A site returning empty/ambiguous history is a data-quality outcome,
        # not a reason to hammer it or invent a different acquisition route.
        for attempt in range(2):
            try:
                data = await _call(fetcher, *args, **kwargs)
                return FetchResult(source=source.name, domain=domain, ok=True, data=data)
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                transient = any(code in message.lower() for code in (
                    "timeout", "timed out", "temporar", "connectionreset",
                    "connection aborted", "429", "502", "503", "504",
                    "remote end closed", "service unavailable",
                ))
                if attempt == 0 and transient:
                    await asyncio.sleep(0.3)
                    continue
                return FetchResult(source=source.name, domain=domain, ok=False, error=message)
        raise AssertionError("unreachable provider retry")

    return list(await asyncio.gather(*(run(source) for source in providers)))


def best_available(results: list[FetchResult]) -> FetchResult | None:
    for result in results:
        if result.ok and result.data not in (None, "", [], {}):
            return result
    return None
