import os
from src.utils.logger import logger
from datetime import datetime
from src.utils.config import *
from src.utils.grid import generate_grid

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)


def build_request():
    url = OPEN_METEO_WEATHER_URL

    params = {
        "latitude": GERMANY_LAT,
        "longitude": GERMANY_LON,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAYLIGHT_VARIABLES),
        "timezone": TIMEZONE
    }

    return url, params


def fetch_daylight(url, params):
    logger.info("Fetching historical daylight data...")

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if "daily" not in data:
        raise ValueError("Open-Meteo response does not contain 'daily' data.")

    return data


def create_dataframe(data):
    df = pd.DataFrame(data["daily"])

    logger.info(f"Created DataFrame with {len(df)} rows.")

    return df


def save_csv(df):
    start = START_DATE.replace("-", "_")
    end = END_DATE.replace("-", "_")

    filename = f"daylight_historical_{start}_{end}.csv"
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    filepath = raw_dir / filename

    df.to_csv(filepath, index=False)
    logger.info(f"Saved daylight data to {filepath}")

    return filepath


def upload_to_s3(filepath):
    filename = os.path.basename(filepath)

    s3_key = (
        f"bronze/daylight/openmeteo/{COUNTRY}/historical/{filename}"
    )

    s3.upload_file(
        Filename=filepath,
        Bucket=S3_BUCKET,
        Key=s3_key
    )

    logger.info(
        f"Uploaded {filename} to s3://{S3_BUCKET}/{s3_key}"
    )

    os.remove(filepath)

    logger.info(f"Deleted local file: {filepath}")

    return s3_key


def main():
    logger.info("Starting Open-Meteo daylight ingestion...")


url, params = build_request()

data = fetch_daylight(url, params)

df = create_dataframe(data)

filepath = save_csv(df)

s3_key = upload_to_s3(filepath)

logger.info(f"S3 Object: {s3_key}")

logger.info("Daylight ingestion completed successfully.")

if __name__ == "__main__":
    main()
