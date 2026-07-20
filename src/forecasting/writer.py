import duckdb

from .config import DATABASE_PATH, FORECAST_TABLE


def write_forecasts(forecast_df):

    with duckdb.connect(DATABASE_PATH) as con:

        con.execute(f"""
        CREATE TABLE IF NOT EXISTS {FORECAST_TABLE} (

            forecast_created_at TIMESTAMP,
            forecast_timestamp TIMESTAMP,
            predicted_generation_mw DOUBLE,
            model_name VARCHAR,
            model_version VARCHAR
        )
        """)

        con.register("forecast_df", forecast_df)

        con.execute(f"""
    INSERT INTO {FORECAST_TABLE}
    (
        forecast_created_at,
        forecast_timestamp,
        predicted_generation_mw,
        model_name,
        model_version
    )
    SELECT
        forecast_created_at,
        forecast_timestamp,
        predicted_generation_mw,
        model_name,
        model_version
    FROM forecast_df
""")

        con.unregister("forecast_df")