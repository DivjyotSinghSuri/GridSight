"""Fault type definitions supported by GridShield's fault injection framework."""

from enum import Enum


class Fault(str, Enum):
    """Enumerates the HTTP-layer faults GridShield can inject into ingestion calls.

    Attributes:
        HTTP_429: simulated rate-limit response (status code 429).
        HTTP_500: simulated server error response (status code 500).
        TIMEOUT: simulated network timeout (raises ``requests.exceptions.Timeout``).
        MALFORMED_JSON: simulated payload corruption — a 200 response whose
            body cannot be parsed by the calling fetcher (invalid JSON for
            the Open-Meteo fetchers, invalid XML for the ENTSO-E fetcher).
    """

    HTTP_429 = "http_429"
    HTTP_500 = "http_500"
    TIMEOUT = "timeout"
    MALFORMED_JSON = "malformed_json"


SUPPORTED_FAULT_PROBABILITIES = (0.0, 0.10, 0.20, 0.25)
"""The fault probabilities the GridShield methodology evaluates, per the spec."""
