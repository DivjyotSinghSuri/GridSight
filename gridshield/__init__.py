"""GridShield: a reproducible engineering methodology for evaluating ELT pipeline resilience.

GridShield is an experimental module that sits on top of GridSight. It never
modifies GridSight's source code, database, or storage — it wraps GridSight's
existing ingestion and transformation functions to measure how reliability
strategies (retry/backoff/checkpointing) and validation strategies
(Python/dbt) behave under injected faults (HTTP 429/500, timeouts, malformed
JSON).
"""
