import os
import requests
import boto3
import pandas as pd
import xml.etree.ElementTree as ET

from dotenv import load_dotenv

from config import *
from logger import logger

load_dotenv()

ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY")

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

def build_request():

    params = {
        "securityToken": ENTSOE_API_KEY,
        "documentType": "A75",
        "processType": "A16",
        "in_Domain": ENTSOE_DOMAIN,
        "periodStart": START_DATE.replace("-", "") + "0000",
        "periodEnd": END_DATE.replace("-", "") + "2300"
    }

    return ENTSOE_URL, params
  
def fetch_generation(url, params):
    logger.info("Fetching generation data from ENTSO-E...")

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    logger.info("Generation data fetched successfully.")

    return response.text

def parse_generation(xml_data):
    """
    Parse ENTSO-E XML response.

    Returns:
        list[dict]
    """
    pass
  
def create_dataframe(records):
    df = pd.DataFrame(records)

    logger.info(f"Created DataFrame with {len(df)} rows.")

    return df
  
def save_csv(df):

    start = START_DATE.replace("-", "_")
    end = END_DATE.replace("-", "_")

    filename = f"generation_historical_{start}_{end}.csv"

    filepath = f"data/raw/{filename}"

    df.to_csv(
        filepath,
        index=False
    )

    logger.info(f"Saved generation data to {filepath}")

    return filepath
  
def upload_to_s3(filepath):

    filename = os.path.basename(filepath)

    s3_key = (
        f"bronze/generation/entsoe/"
        f"{COUNTRY}/historical/{filename}"
    )

    s3.upload_file(
        Filename=filepath,
        Bucket=S3_BUCKET,
        Key=s3_key
    )

    logger.info(f"Uploaded {filename} to s3://{S3_BUCKET}/{s3_key}")

    os.remove(filepath)

    logger.info(f"Deleted local file: {filepath}")

    return s3_key
  
def parse_generation(xml_data):