import streamlit as st
from pathlib import Path

from ..config import SHAP_IMAGE_PATH


def render_model_insights():
    st.title("🔮 Model Insights")
    st.caption(
        "Full-history evaluation and model explainability. If SHAP artifacts are available, feature importance and diagnostics will be shown."
    )

    try:
        from ..components.utils import load_metrics

        metrics = load_metrics()

        st.subheader("Model Summary")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Model", metrics.get("model_name", "—"))
        with c2:
            st.metric("Version", metrics.get("model_version", "—"))
        with c3:
            wape = metrics.get("test_wape_pct", None)
            st.metric("Test WAPE", f"{wape:.2f}%" if wape is not None else "N/A")

        # SHAP visualization if available
        shap_path = Path(SHAP_IMAGE_PATH)
        if shap_path.exists():
            st.subheader("Feature Importance")
            st.image(str(shap_path), use_column_width=True)
            st.caption("SHAP summary plot from model evaluation artifacts.")
        else:
            st.info(
                "Feature importance visualization is not available. "
                "SHAP artifacts are not present in the models/ directory."
            )

    except Exception:
        st.info("Model metrics unavailable.")
