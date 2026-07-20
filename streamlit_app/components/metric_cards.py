"""Reusable metric-card rendering (built on st.metric, styled via app-level CSS)."""

from typing import Optional

import streamlit as st


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
) -> None:
    """Render a single metric card."""
    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text,
    )


def metric_row(items: list) -> None:
    """
    Render a row of metric cards.

    Supported formats:

    1. Dictionary
    {
        "label": "...",
        "value": "...",
        "delta": "...",      # optional
        "help": "..."        # optional
    }

    2. Tuple
    ("Label", "Value")
    """

    if not items:
        return

    cols = st.columns(len(items))

    for col, item in zip(cols, items):
        with col:

            # Support tuple format
            if isinstance(item, tuple):
                label, value = item
                metric_card(
                    label=label,
                    value=value,
                )

            # Support dictionary format
            elif isinstance(item, dict):
                metric_card(
                    label=item["label"],
                    value=item["value"],
                    delta=item.get("delta"),
                    help_text=item.get("help"),
                )

            else:
                raise TypeError(
                    f"metric_row() expected dict or tuple, got {type(item).__name__}"
                )