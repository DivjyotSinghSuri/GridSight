import os
from logger import logger
from datetime import datetime
from config import *
from utils.grid import generate_grid

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

def build_request(lat, lon):
  url = OPEN_METEO_WEATHER_URL
  
  params = {
    "latitude": lat,
    "longitude": lon,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ",".join(WEATHER_VARIABLES),
    "timezone": TIMEZONE
}
  return url, params

def fetch_weather(url, params):
  logger.info("Fetching historical weather data...")
  
  response = requests.get(
    url,
    params=params,
    timeout=60)
    
  response.raise_for_status()
    
  data = response.json()
    
  if "hourly" not in data:
    raise ValueError("Open-Meteo response does not contain 'hourly' data.")
  
  return data

def create_dataframe(data):
  df = pd.DataFrame(data["hourly"])
  logger.info(f"Created DataFrame with {len(df)} rows.")
  return df

def save_csv(df, grid_id):
  start = START_DATE.replace("-", "_")
  end = END_DATE.replace("-", "_")

  filename = f"weather_historical_{start}_{end}.csv"
  filepath = f"data/raw/{filename}"
  
  df.to_csv(
    filepath,
    index=False
)
  logger.info(f"Saved weather data to {filepath}")
  
  return filepath

def upload_to_s3(filepath, grid_id):
  filename = os.path.basename(filepath)
  s3_key = (
    f"bronze/weather/openmeteo/{COUNTRY}/"
    f"{grid_id}/{filename}"
)  
  s3.upload_file(
      Filename=filepath,
      Bucket=S3_BUCKET,
      Key=s3_key)
    
  logger.info(f"Uploaded {filename} to s3://{S3_BUCKET}/{s3_key}")

  os.remove(filepath)
  logger.info(f"Deleted local file: {filepath}")

  return s3_key

def main():
    logger.info("Starting Open-Meteo weather ingestion...")

    grid_points = generate_grid()

    successful_uploads = 0

    try:
        for grid_id, lat, lon in grid_points:

            try:
                logger.info(f"Processing {grid_id} ({lat}, {lon})")

                url, params = build_request(lat, lon)

                data = fetch_weather(url, params)

                df = create_dataframe(data)

                filepath = save_csv(df, grid_id)

                s3_key = upload_to_s3(filepath, grid_id)

                logger.info(f"{grid_id} uploaded successfully.")
                logger.info(f"S3 Object: {s3_key}")

                successful_uploads += 1

            except Exception as e:
                logger.exception(f"{grid_id} failed: {e}")
                continue

        logger.info(
            f"Weather ingestion completed. Successfully uploaded "
            f"{successful_uploads}/{len(grid_points)} grid points."
        )

    except Exception as e:
        logger.exception(f"Weather ingestion failed: {e}")

    finally:
        logger.info("Pipeline execution finished.")


if __name__ == "__main__":
    main()