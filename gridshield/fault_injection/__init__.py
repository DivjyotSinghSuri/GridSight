"""Reproducible HTTP fault injection for GridSight's ingestion fetchers.

GridShield never modifies ``src/ingestion/*.py``. Instead it monkeypatches
``requests.get`` for the scope of a single wrapped call, deterministically
routing each outbound call to either a simulated fault (HTTP 429, HTTP 500,
timeout, malformed JSON) or a synthetic-but-realistic success response built
from a recorded fixture, based on a seeded random draw.
"""
