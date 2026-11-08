"""Deterministic, scoped fault injection into GridSight's ``requests.get`` calls.

:class:`FaultInjector` is a context manager. While active, it replaces the
module-level ``requests.get`` function (the only HTTP entry point GridSight's
four ingestion fetchers use) with a routing function that, per call and
based on a seeded random draw, either:

* returns a synthetic-but-realistic success response built from a recorded
  fixture (see ``gridshield/fault_injection/fixtures/``), or
* simulates the configured :class:`~gridshield.fault_injection.faults.Fault`.

No real network call is ever made while a :class:`FaultInjector` is active.
``requests.get`` is always restored on exit, even if the wrapped code
raises, so the patch can never leak beyond its ``with`` block.
"""

import json
import random
from pathlib import Path
from typing import Optional

import requests

from gridshield.configs.settings import FIXTURES_DIR
from gridshield.fault_injection.experiment_log import ExperimentLog
from gridshield.fault_injection.faults import Fault


class MockResponse:
    """A minimal stand-in for ``requests.Response`` used to synthesize both faults and successes.

    Only implements the surface GridSight's fetchers actually use:
    ``status_code``, ``.text``, ``.json()``, and ``.raise_for_status()``.
    """

    def __init__(self, status_code: int, text: str, json_ok: bool = True):
        """Build a mock response.

        Args:
            status_code: the HTTP status code to report.
            text: the raw response body.
            json_ok: if ``False``, ``.json()`` raises
                ``requests.exceptions.JSONDecodeError`` instead of parsing
                ``text``, simulating a corrupted payload.
        """
        self.status_code = status_code
        self.text = text
        self._json_ok = json_ok

    def json(self):
        """Parse ``.text`` as JSON, or raise ``JSONDecodeError`` if this response simulates a malformed body."""
        if not self._json_ok:
            raise requests.exceptions.JSONDecodeError(
                "Expecting value: malformed JSON body (simulated by GridShield)",
                self.text,
                0,
            )
        return json.loads(self.text)

    def raise_for_status(self):
        """Raise ``requests.exceptions.HTTPError`` if ``status_code`` indicates a client/server error."""
        if 400 <= self.status_code:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Error (simulated by GridShield)", response=self
            )


def _detect_source(params: Optional[dict]) -> str:
    """Best-effort classification of which GridSight data source a call belongs to.

    Inspects the ``params`` dict passed to ``requests.get`` (the same dicts
    built by ``src/ingestion/{weather,irradiance,daylight,generation}.py``)
    without importing or modifying those modules.

    Args:
        params: the ``params`` keyword argument passed to ``requests.get``.

    Returns:
        str: one of ``"weather"``, ``"irradiance"``, ``"daylight"``,
        ``"generation"``, or ``"unknown"``.
    """
    if not params:
        return "unknown"
    if "documentType" in params or "securityToken" in params:
        return "generation"
    if "daily" in params:
        return "daylight"
    hourly = params.get("hourly", "")
    if "shortwave_radiation" in hourly:
        return "irradiance"
    if "temperature_2m" in hourly:
        return "weather"
    return "unknown"


_FIXTURE_FILES = {
    "weather": FIXTURES_DIR / "weather_hourly.json",
    "irradiance": FIXTURES_DIR / "irradiance_hourly.json",
    "daylight": FIXTURES_DIR / "daylight_daily.json",
    "generation": FIXTURES_DIR / "generation.xml",
}


def _load_fixture_text(source: str) -> str:
    """Read the recorded fixture body for a given source, falling back to an empty JSON object.

    Args:
        source: one of the keys in ``_FIXTURE_FILES``.

    Returns:
        str: the raw fixture file contents.
    """
    fixture_path = _FIXTURE_FILES.get(source)
    if fixture_path is None or not fixture_path.exists():
        return "{}"
    return fixture_path.read_text()


class FaultInjector:
    """Context manager that deterministically routes ``requests.get`` calls to faults or fixtures.

    Example:
        >>> with FaultInjector(Fault.HTTP_429, probability=0.2, seed=42,
        ...                    scenario_id="s1", run_number=0) as injector:
        ...     fetch_weather(52.5, 13.4, "2026-07-25", "2026-07-25")
        >>> injector.log.to_dict()["total_calls"]
        1
    """

    def __init__(
        self,
        fault_type: Optional[Fault],
        probability: float,
        seed: int,
        scenario_id: str = "scenario",
        run_number: int = 0,
    ):
        """Configure a fault injector.

        Args:
            fault_type: which fault to inject, or ``None``/probability 0 to
                only ever return synthetic success responses.
            probability: probability (0.0-1.0) that any given call is faulted.
            seed: seed driving the per-call random draws; identical seeds
                reproduce identical fault sequences.
            scenario_id: identifier recorded in the resulting
                :class:`ExperimentLog`.
            run_number: repetition index recorded in the resulting
                :class:`ExperimentLog`.
        """
        self.fault_type = fault_type
        self.probability = probability
        self.seed = seed
        self.log = ExperimentLog(
            scenario_id=scenario_id,
            run_number=run_number,
            seed=seed,
            fault_type=fault_type.value if fault_type else None,
            fault_probability=probability,
        )
        self._rng = random.Random(seed)
        self._original_get = None

    def __enter__(self) -> "FaultInjector":
        """Patch ``requests.get`` and begin routing calls; returns ``self``."""
        self._original_get = requests.get
        requests.get = self._routed_get
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Restore the original ``requests.get`` unconditionally."""
        requests.get = self._original_get
        return False

    def _routed_get(self, url, params=None, timeout=None, **kwargs):
        """Replacement for ``requests.get``: decides fault-vs-success and returns/raises accordingly."""
        source = _detect_source(params)
        draw = self._rng.random()
        should_fault = self.fault_type is not None and draw < self.probability

        self.log.record_call(
            source_hint=source,
            faulted=should_fault,
            fault_type=self.fault_type.value if should_fault else None,
            random_draw=draw,
        )

        if not should_fault:
            return MockResponse(status_code=200, text=_load_fixture_text(source))

        return self._simulate_fault(source)

    def _simulate_fault(self, source: str):
        """Produce the response (or raise the exception) matching ``self.fault_type``.

        Args:
            source: the detected data source, used to pick a fixture body
                for faults that still return a 200-shaped envelope
                (currently unused but kept for parity with ``_routed_get``).

        Returns:
            MockResponse: for ``HTTP_429``, ``HTTP_500``, and
            ``MALFORMED_JSON``.

        Raises:
            requests.exceptions.Timeout: for ``TIMEOUT``.
        """
        if self.fault_type is Fault.HTTP_429:
            return MockResponse(status_code=429, text="")
        if self.fault_type is Fault.HTTP_500:
            return MockResponse(status_code=500, text="Internal Server Error")
        if self.fault_type is Fault.TIMEOUT:
            raise requests.exceptions.Timeout(
                "Request timed out (simulated by GridShield)"
            )
        if self.fault_type is Fault.MALFORMED_JSON:
            fixture_text = _load_fixture_text(source)
            corrupted = fixture_text[: max(0, len(fixture_text) // 2)] + "<<CORRUPT>>"
            return MockResponse(status_code=200, text=corrupted, json_ok=False)
        raise ValueError(f"Unsupported fault type: {self.fault_type}")
