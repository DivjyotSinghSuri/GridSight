"""
Dashboard-level configuration: paths, styling, static metadata.

This is intentionally separate from the inference pipeline's config.py.
The dashboard only ever READS existing artifacts -- it never trains,
writes, or mutates anything in DuckDB.
"""
from pathlib import Path
from config import DATABASE_PATH, MODEL_DIR as ROOT_MODELS_DIR, ASSETS_DIR as ROOT_ASSETS_DIR

# Static fallback metrics -- used only if METRICS_PATH is not found yet.
# Replace by exporting a real metrics.json after model evaluation.
FALLBACK_METRICS = {
    "model_name": "Ridge Regression",
    "model_version": "v1.0",
    "test_wape_pct": 7.79,
    "alpha": 99.819268,
}

MODELS_DIR = ROOT_MODELS_DIR
METRICS_PATH = MODELS_DIR / "metrics.json"
SHAP_IMAGE_PATH = MODELS_DIR / "shap_summary.png"
COMPARISON_IMAGE_PATH = MODELS_DIR / "model_comparison.png"
ABLATION_IMAGE_PATH = MODELS_DIR / "feature_ablation.png"
PRED_VS_ACTUAL_IMAGE_PATH = MODELS_DIR / "prediction_vs_actual.png"

ASSETS_DIR = ROOT_ASSETS_DIR
DAG_IMAGE_PATH = ASSETS_DIR / "airflow_dag.png"
DBT_LINEAGE_IMAGE_PATH = ASSETS_DIR / "dbt_lineage.png"
LOGO_PATH = ASSETS_DIR / "gridsight_logo.png"

FORECAST_TABLE = "gold_forecasts"
GENERATION_VIEW = "stg_generation"
WEATHER_VIEW = "stg_weather"
IRRADIANCE_VIEW = "stg_irradiance"
DAYLIGHT_VIEW = "stg_daylight"

PRIMARY_COLOR = "#2E5EAA"
ACCENT_COLOR = "#F2A541"
MUTED_TEXT_COLOR = "#6B7280"

PAGE_TITLE = "GridSight"
PAGE_ICON = "☀️"

NAV_PAGES = ["Overview", "Forecast", "Weather",
             "Model Insights", "Pipeline Status"]
