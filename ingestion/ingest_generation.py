import os
import requests
import boto3
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv

from config import *
from logger import logger

load_dotenv()


s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

def generate_monthly_ranges(start_date, end_date):

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    ranges = []

    current = start

    while current < end:

        next_month = current + relativedelta(months=1)

        ranges.append((
            current.strftime("%Y%m%d0000"),
            next_month.strftime("%Y%m%d0000")
        ))

        current = next_month

    return ranges

def build_request(period_start, period_end):

    url = ENTSOE_ENDPOINT

    params = {
        "securityToken": ENTSOE_API_KEY,
        "documentType": "A75",
        "processType": "A16",
        "in_Domain": GERMANY_DOMAIN,
        "periodStart": period_start,
        "periodEnd": period_end}

    return url, params


def fetch_generation(url, params):
    logger.info("Fetching generation data from ENTSO-E...")

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    # print(response.status_code)
    # print(response.text)

    response.raise_for_status()

    logger.info("Generation data fetched successfully.")

    return response.text


PSR_TYPES = {
    "B01": "Biomass",
    "B02": "Fossil Brown Coal/Lignite",
    "B04": "Fossil Gas",
    "B05": "Fossil Hard Coal",
    "B09": "Geothermal",
    "B10": "Hydro Pumped Storage",
    "B11": "Hydro Run-of-river",
    "B12": "Hydro Water Reservoir",
    "B14": "Nuclear",
    "B16": "Solar",
    "B18": "Wind Offshore",
    "B19": "Wind Onshore",
    "B20": "Other"
}


def parse_generation(xml_data):

    logger.info("Parsing ENTSO-E XML...")

    root = ET.fromstring(xml_data)

    namespace = {
        "ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"
    }

    records = []

    for series in root.findall("ns:TimeSeries", namespace):

        psr_code = series.find(
            "ns:MktPSRType/ns:psrType",
            namespace
        ).text

        production_type = PSR_TYPES.get(psr_code, psr_code)

        period = series.find(
            "ns:Period",
            namespace
        )

        start = period.find(
            "ns:timeInterval/ns:start",
            namespace
        ).text

        start_time = datetime.strptime(
            start,
            "%Y-%m-%dT%H:%MZ"
        )

        for point in period.findall("ns:Point", namespace):

            position = int(point.find("ns:position",namespace).text)

            quantity = float(point.find("ns:quantity",namespace).text)

            timestamp = start_time + timedelta(minutes=(position - 1) * 15)

            records.append({
                "timestamp": timestamp,
                "production_type": production_type,
                "generation_mw": quantity
            })

    logger.info(f"Parsed {len(records)} generation records.")

    return records


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


def main():

    all_records = []

    ranges = generate_monthly_ranges(
        START_DATE,
        END_DATE
    )

    for period_start, period_end in ranges:

        logger.info(
            f"Processing {period_start} -> {period_end}"
        )

        url, params = build_request(
            period_start,
            period_end
        )

        xml = fetch_generation(
            url,
            params
        )

        records = parse_generation(xml)

        all_records.extend(records)

    df = create_dataframe(all_records)

    filepath = save_csv(df)

    upload_to_s3(filepath)

    logger.info("Generation ingestion completed successfully.")

if __name__ == "__main__":
    main()
