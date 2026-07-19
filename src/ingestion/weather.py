import requests
import time
import pandas as pd

from requests.exceptions import RequestException

from src.utils.config import (
    OPEN_METEO_WEATHER_URL,
    WEATHER_VARIABLES,
    TIMEZONE
)
from src.utils.logger import logger


def _build_request(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(WEATHER_VARIABLES),
        "timezone": TIMEZONE,
    }

    return OPEN_METEO_WEATHER_URL, params


def _request_weather(url, params, lat, lon, start_date, end_date):
    logger.info(
        f"Fetching weather data for ({lat}, {lon}) "
        f"from {start_date} to {end_date}."
    )

    max_retries = 5

    for attempt in range(max_retries):

        try:
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

            if "hourly" not in data:
                raise ValueError(
                    "Open-Meteo response does not contain 'hourly' data."
                )

            time.sleep(3)

            df = pd.DataFrame(data["hourly"])

            logger.info(f"Retrieved {len(df)} hourly records.")

            return df

        except RequestException as e:

            if attempt == max_retries - 1:
                raise

            wait = 10 * (attempt + 1)

            logger.warning(
                f"Request failed ({e}). Retrying in {wait} seconds..."
            )

            time.sleep(wait)

    raise Exception("Maximum retries exceeded.")


def fetch_weather(lat, lon, start_date, end_date):
    url, params = _build_request(
        lat,
        lon,
        start_date,
        end_date
    )

    return _request_weather(
        url,
        params,
        lat,
        lon,
        start_date,
        end_date
    )