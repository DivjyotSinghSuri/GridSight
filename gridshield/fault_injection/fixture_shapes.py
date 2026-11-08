"""Computes each source's expected row count directly from its recorded fixture.

Used by ``metrics/reliability_metrics.py`` to define Data Completeness as
the fraction of *rows* successfully captured (row-weighted), distinct from
Recovery Rate's fraction of *units of work* that succeeded (unit-weighted).
Row counts are derived from the fixture files themselves — the same files
:class:`~gridshield.fault_injection.injector.FaultInjector` serves as a
"successful" response — so this can never drift out of sync with what a
successful fetch actually returns.
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict

from gridshield.configs.settings import FIXTURES_DIR

_GENERATION_NAMESPACE = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}


def _weather_like_row_count(fixture_filename: str, envelope_key: str) -> int:
    """Count rows in a weather/irradiance/daylight-shaped JSON fixture.

    Args:
        fixture_filename: fixture file under ``fault_injection/fixtures/``.
        envelope_key: ``"hourly"`` or ``"daily"``, matching Open-Meteo's envelope.

    Returns:
        int: number of rows the fixture's first data column contains.
    """
    with open(FIXTURES_DIR / fixture_filename) as f:
        data = json.load(f)
    first_column = next(iter(data[envelope_key].values()))
    return len(first_column)


def _generation_row_count(fixture_filename: str) -> int:
    """Count ``<Point>`` elements across all ``<TimeSeries>`` in the ENTSO-E XML fixture.

    Args:
        fixture_filename: fixture file under ``fault_injection/fixtures/``.

    Returns:
        int: total number of generation data points the fixture contains.
    """
    root = ET.parse(FIXTURES_DIR / fixture_filename).getroot()
    return sum(
        len(series.findall("ns:Period/ns:Point", _GENERATION_NAMESPACE))
        for series in root.findall("ns:TimeSeries", _GENERATION_NAMESPACE)
    )


def _compute_expected_rows_per_source() -> Dict[str, int]:
    """Build the source -> expected-row-count mapping from the recorded fixtures."""
    return {
        "weather": _weather_like_row_count("weather_hourly.json", "hourly"),
        "irradiance": _weather_like_row_count("irradiance_hourly.json", "hourly"),
        "daylight": _weather_like_row_count("daylight_daily.json", "daily"),
        "generation": _generation_row_count("generation.xml"),
    }


EXPECTED_ROWS_PER_SOURCE: Dict[str, int] = _compute_expected_rows_per_source()
"""Row count a successful fetch returns for each source, derived from its fixture."""
