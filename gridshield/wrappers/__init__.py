"""Wrappers around GridSight's existing functions.

Every module in this package calls GridSight's real, unmodified functions
(fetchers, bronze SQL patterns, dbt) and adds metrics collection around
them. GridShield never edits GridSight source files. The one exception,
driven by the storage-isolation requirement, is the local bronze/DuckDB
sink: since GridSight's ``write_bronze``/``load_bronze`` always target the
real S3 bucket and production DuckDB file, GridShield reimplements their
storage layout locally (see ``bronze_sink.py`` and
``bronze_load_wrapper.py``) rather than modifying them to accept an
alternate destination.
"""
