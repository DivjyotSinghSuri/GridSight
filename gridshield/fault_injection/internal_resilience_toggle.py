"""Toggle for GridSight's own (pre-GridShield) fetcher-level retry loop.

Chapter 12.1 of the project handbook documents the "internal-retry
confound": ``src/ingestion/{weather,irradiance,daylight,generation}.py``
each retry ``RequestException`` (which covers HTTP 429/500, timeouts, and,
for three of the four fetchers, malformed-JSON via ``JSONDecodeError``)
internally, up to ``MAX_RETRIES`` times, *before* GridShield's own
reliability layer is ever invoked. This means GridShield's four reliability
strategies are normally benchmarked against a pipeline that already has its
own resilience built in.

:func:`disable_gridsight_internal_resilience` sets each fetcher module's
``MAX_RETRIES`` to 1 for the duration of the ``with`` block, so the very
first fault raises straight up to GridShield's reliability layer, exactly
as if GridSight's fetchers never retried at all. It changes no other
behavior: the retry loops, exception handling, and control flow inside the
fetchers are completely untouched, and ``MAX_RETRIES`` is restored
unconditionally on exit. Outside this context manager (e.g. every existing
resilient-experiment run), ``MAX_RETRIES`` stays at its original default of
5 and behavior is byte-for-byte unchanged.
"""

from contextlib import contextmanager

from src.ingestion import daylight, generation, irradiance, weather

_FETCHER_MODULES = (weather, irradiance, daylight, generation)


@contextmanager
def disable_gridsight_internal_resilience():
    """Force every GridSight fetcher's internal retry budget to 1 for the duration of the block."""
    originals = [module.MAX_RETRIES for module in _FETCHER_MODULES]
    for module in _FETCHER_MODULES:
        module.MAX_RETRIES = 1
    try:
        yield
    finally:
        for module, original in zip(_FETCHER_MODULES, originals):
            module.MAX_RETRIES = original
