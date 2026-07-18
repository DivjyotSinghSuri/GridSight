from datetime import datetime, timedelta

from src.ingestion.weather import fetch_weather
from src.ingestion.irradiance import fetch_irradiance
from src.ingestion.daylight import fetch_daylight
from src.ingestion.generation import fetch_generation
from src.ingestion.bronze_writer import write_bronze

from src.utils.grid import generate_grid
from src.utils.logger import logger


def main():
    """
    Executes the daily Bronze ingestion pipeline.
    """

    logger.info("Starting Bronze ingestion pipeline.")

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=1)

    grid_points = generate_grid()

    logger.info(f"Processing {len(grid_points)} grid points.")

    for grid_id, lat, lon in grid_points:

        logger.info(f"Processing Grid {grid_id}")

        # Weather
        weather_df = fetch_weather(
            lat,
            lon,
            start_date,
            end_date
        )

        write_bronze(
    df=weather_df,
    source="weather/openmeteo",
    folder=grid_id,
    filename=f"{start_date:%Y%m%d}.csv"
)

        # Irradiance
        irradiance_df = fetch_irradiance(
            lat,
            lon,
            start_date,
            end_date
        )

        write_bronze(
    df=irradiance_df,
    source="irradiance/openmeteo",
    folder=grid_id,
    filename=f"{start_date:%Y%m%d}.csv"
)

    logger.info("Weather and irradiance ingestion completed.")

    # Daylight
    daylight_df = fetch_daylight(
        start_date,
        end_date
    )

    write_bronze(
    df=daylight_df,
    source="daylight/openmeteo",
    filename=f"{start_date:%Y%m%d}.csv"
)

    logger.info("Daylight ingestion completed.")

    # Generation
    generation_df = fetch_generation(
        start_date,
        end_date
    )

    write_bronze(
    df=generation_df,
    source="generation/entsoe",
    filename=f"{start_date:%Y%m%d}.csv"
)

    logger.info("Generation ingestion completed.")

    logger.info("Bronze ingestion pipeline completed successfully.")


if __name__ == "__main__":
    main()