import requests
import time
import pandas as pd

from src.utils.config import (
    OPEN_METEO_WEATHER_URL,
    GERMANY_LAT,
    GERMANY_LON,
    DAYLIGHT_VARIABLES,
    TIMEZONE
)
from src.utils.logger import logger

def _build_request(start_date, end_date):
    params = {
    "latitude": GERMANY_LAT,
    "longitude": GERMANY_LON,
    "start_date": start_date,
    "end_date": end_date,
    "daily": DAYLIGHT_VARIABLES,
    "timezone": TIMEZONE,
}

    return OPEN_METEO_WEATHER_URL, params
  
def _request_daylight(url, params, start_date, end_date):
    logger.info(
        f"Fetching daylight data "
        f"from {start_date} to {end_date}."
    )

    max_retries = 5

    for attempt in range(max_retries):

        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        if response.status_code == 429:
            wait = 30 * (attempt + 1)
            logger.warning(
                f"Rate limited (429). Retrying in {wait} seconds..."
            )
            time.sleep(wait)
            continue

        response.raise_for_status()

        data = response.json()

        if "daily" not in data:
            raise ValueError(
                "Open-Meteo response does not contain 'daily' data."
            )

        time.sleep(3)
        df = pd.DataFrame(data["daily"])

        logger.info(f"Retrieved {len(df)} daily daylight records.")

        return df

    raise Exception("Maximum retries exceeded due to repeated rate limiting.")

def fetch_daylight(start_date, end_date):
    """
    Fetches hourly daylight data from Open-Meteo.

    Returns:
        pandas.DataFrame
    """
    url, params = _build_request(
        start_date,
        end_date
    )

    df = _request_daylight(
        url,
        params,
        start_date,
        end_date
    )

    return df

    