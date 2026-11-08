"""GridShield's Reliability Layer: fixed retry, exponential backoff, and backoff-with-checkpointing.

Each strategy implements the common :class:`~gridshield.reliability.base.ReliabilityStrategy`
interface so the benchmark engine can swap strategies purely through
configuration.
"""
