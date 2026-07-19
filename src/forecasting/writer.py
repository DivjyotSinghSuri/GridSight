import duckdb
from .config import DATABASE_PATH, FORECAST_TABLE


def write_forecasts(forecast_df):
    """
    Writes the latest forecasts to the gold_forecasts table.
    Replaces the existing table on each run.
    """

    with duckdb.connect(DATABASE_PATH) as con:
      con.register("forecast_df", forecast_df)

      con.execute(f"""
          CREATE OR REPLACE TABLE {FORECAST_TABLE} AS
          SELECT *
          FROM forecast_df
      """)

      con.unregister("forecast_df")