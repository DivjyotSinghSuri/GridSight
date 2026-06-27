import os
import logging
from datetime import datetime
from config import LATITUDE, LONGITUDE, START_DATE, END_DATE, CITY

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv

def build_request():
  url = OPEN_METEO_URL
  
  params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ",".join(HOURLY_VARIABLES),
    "timezone": TIMEZONE
}
  return url, params

def fetch_weather(url, params):
  logging.info("Fetching historical weather data...")
  
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
  logging.info("Created DataFrame with {len(df)} rows.")
  return df

def save_csv(df):
  start = START_DATE.replace("-", "_")
  end = END_DATE.replace("-", "_")
  filename = f"weather_historical_{start}_{end}.csv"
  
  filepath = f"data/raw/{filename}"
  
  df.to_csv(
    filepath,
    index=False
)
  logging.info(f"Saved weather data to {filepath}")
  
  return filepath

def upload_to_s3(filepath):
  