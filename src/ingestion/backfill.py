from datetime import datetime, timedelta

from src.ingestion.weather import fetch_weather
from src.ingestion.irradiance import fetch_irradiance
from src.ingestion.daylight import fetch_daylight
from src.ingestion.generation import fetch_generation
from src.ingestion.bronze_writer import write_bronze

from src.utils.grid import generate_grid
from src.utils.logger import logger


BACKFILL_DAYS = 14


def main():
    """
    Backfills the previous N days of Bronze data into S3.
    Run this once before enabling the Airflow DAG.
    """

    logger.info(f"Starting {BACKFILL_DAYS}-day Bronze backfill.")

    grid_points = generate_grid()

    logger.info(f"Processing {len(grid_points)} grid points.")

    today = datetime.today().date()

    # Oldest → newest
    for days_ago in range(BACKFILL_DAYS, 0, -1):

        current_date = today - timedelta(days=days_ago)

        logger.info(f"Processing {current_date}")

        # ------------------------
        # Weather & Irradiance
        # ------------------------

        for grid_id, lat, lon in grid_points:

            logger.info(f"Grid {grid_id}")

            weather_df = fetch_weather(
                lat,
                lon,
                current_date,
                current_date
            )

            write_bronze(
                df=weather_df,
                source="weather/openmeteo",
                folder=grid_id,
                filename=f"{current_date:%Y%m%d}.csv"
            )

            irradiance_df = fetch_irradiance(
                lat,
                lon,
                current_date,
                current_date
            )

            write_bronze(
                df=irradiance_df,
                source="irradiance/openmeteo",
                folder=grid_id,
                filename=f"{current_date:%Y%m%d}.csv"
            )

        logger.info(
            f"Weather and irradiance completed for {current_date}."
        )

        # ------------------------
        # Daylight
        # ------------------------

        daylight_df = fetch_daylight(
            current_date,
            current_date
        )

        write_bronze(
            df=daylight_df,
            source="daylight/openmeteo",
            filename=f"{current_date:%Y%m%d}.csv"
        )

        logger.info(f"Daylight completed for {current_date}.")

        # ------------------------
        # Generation
        # ------------------------

        generation_df = fetch_generation(
            current_date,
            current_date
        )

        write_bronze(
            df=generation_df,
            source="generation/entsoe",
            filename=f"{current_date:%Y%m%d}.csv"
        )

        logger.info(f"Generation completed for {current_date}.")

    logger.info("Bronze backfill completed successfully.")


if __name__ == "__main__":
    main()