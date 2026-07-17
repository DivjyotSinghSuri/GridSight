DATASET_COLUMNS = [
    "timestamp",

    # Weather Features
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "cloud_cover_pct",
    "wind_speed_kmh",

    # Irradiance Features
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",

    # Calendar Features
    "hour",
    "month",
    "day_of_week",
    "day_of_year",
    "is_weekend",
    "year",

    # Lag Features
    "solar_generation_mw_lag_1h",
    "solar_generation_mw_lag_24h",
    "solar_generation_mw_lag_168h",

    # Rolling Mean
    "solar_generation_mw_roll_mean_3h",
    "solar_generation_mw_roll_mean_6h",
    "solar_generation_mw_roll_mean_24h",

    # Rolling Std
    "solar_generation_mw_roll_std_3h",
    "solar_generation_mw_roll_std_6h",
    "solar_generation_mw_roll_std_24h",

    # Rolling Min
    "solar_generation_mw_roll_min_3h",
    "solar_generation_mw_roll_min_6h",
    "solar_generation_mw_roll_min_24h",

    # Rolling Max
    "solar_generation_mw_roll_max_3h",
    "solar_generation_mw_roll_max_6h",
    "solar_generation_mw_roll_max_24h",

    # Daylight Features
    "daylight_duration_hours",
    "sunshine_duration_hours",
    "is_daylight",
    "minutes_since_sunrise",
    "daylight_progress_pct",

    # Interaction Features
    "cloud_shortwave_interaction",
    "temperature_shortwave_interaction",
    "wind_temperature_interaction",
    "daylight_progress_shortwave_interaction",
]

MODEL_FEATURES = DATASET_COLUMNS[1:]

DATABASE_PATH = "../gridsight.duckdb"

PRODUCTION_MODEL_PATH = "../models/production_model.joblib"

FORECAST_TABLE = "gold_forecasts"