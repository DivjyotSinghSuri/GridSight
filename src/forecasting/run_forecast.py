import duckdb
from .config import DATABASE_PATH
from .predictor import run_prediction
from .validator import validate_dataset
from .writer import write_forecasts


def load_forecast_dataset():
    """
    Loads the forecast feature dataset from DuckDB.
    """

    with duckdb.connect(str(DATABASE_PATH)) as con:
        forecast_df = con.execute("""
            SELECT *
            FROM gold_forecast_features
        """).df()

        print(forecast_df.shape)
        print(forecast_df.head())

    return forecast_df


def run_forecast():
    df = load_forecast_dataset()

    validate_dataset(df)

    forecast_df = run_prediction(df)

    write_forecasts(forecast_df)


if __name__ == "__main__":
    run_forecast()
