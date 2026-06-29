import os
from logger import logger
from datetime import datetime
from config import *

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

def build_request():
  url = OPEN_METEO_SOLAR_URL
  
  params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ",".join(SOLAR_VARIABLES),
    "timezone": TIMEZONE
}
  return url, params

def fetch_irradiance(url, params):
  logger.info("Fetching historical solar irradiance data...")
  
  response = requests.get(
    url,
    params=params,
    timeout=60)
    
  response.raise_for_status()
    
  data = response.json()
    
  if "hourly" not in data:
    raise ValueError("Open-Meteo Solar response does not contain 'hourly' data.")
  
  return data

def create_dataframe(data):
  df = pd.DataFrame(data["hourly"])
  logger.info(f"Created DataFrame with {len(df)} rows.")
  return df

def save_csv(df):
  start = START_DATE.replace("-", "_")
  end = END_DATE.replace("-", "_")
  filename = f"solar_irradiance_historical_{start}_{end}.csv"
  
  filepath = f"data/raw/{filename}"
  
  df.to_csv(
    filepath,
    index=False
)
  logger.info(f"Saved irradiance data to {filepath}")
  
  return filepath

def upload_to_s3(filepath):
  filename = os.path.basename(filepath)
  s3_key = (f"bronze/irradiance/openmeteo_solar/{CITY}/historical/{filename}")
    
  s3.upload_file(
      Filename=filepath,
      Bucket=S3_BUCKET,
      Key=s3_key)
    
  logger.info(f"Uploaded {filename} to s3://{S3_BUCKET}/{s3_key}")

  os.remove(filepath)
  logger.info(f"Deleted local file: {filepath}")

  return s3_key

def main():
    try:
      logger.info("Starting Open-Meteo solar irradiance historical ingestion...")

      url, params = build_request()

      data = fetch_irradiance(url, params)

      df = create_dataframe(data)

      filepath = save_csv(df)

      s3_key = upload_to_s3(filepath)

      logger.info("Open-Meteo solar irradiance historical ingestion completed successfully.")
      logger.info(f"S3 Object: {s3_key}")
    
    except Exception as e:
      logger.exception(f"Open-Meteo ingestion failed: {e}")
    finally:
      logger.info("Pipeline execution finished.")
    
      
    
if __name__ == "__main__":
    main()