import os
import boto3
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta

from config import DATA_DIR
from src.utils.config import (
    COUNTRY,
    S3_BUCKET
)
from src.utils.logger import logger

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)


def _save_csv(df, filename):
    """
    Saves a DataFrame locally and returns the file path.
    """

    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    filepath = raw_dir / filename

    df.to_csv(
        filepath,
        index=False
    )

    logger.info(f"Saved {filename} locally.")

    return filepath


def _upload_to_s3(filepath, source, folder=None):
    """
    Uploads a local CSV to the Bronze layer in S3.
    """

    filename = os.path.basename(filepath)

    if folder:
        s3_key = (
            f"bronze/"
            f"{source}/"
            f"{COUNTRY}/"
            f"daily/"
            f"{folder}/"
            f"{filename}"
        )
    else:
        s3_key = (
            f"bronze/"
            f"{source}/"
            f"{COUNTRY}/"
            f"daily/"
            f"{filename}"
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


def write_bronze(
    df,
    source,
    filename,
    folder=None
):
    """
    Writes a DataFrame to the Bronze layer.

    Args:
        df (pd.DataFrame)
        source (str):
            weather/openmeteo
            irradiance/openmeteo
            daylight/openmeteo
            generation/entsoe
        filename (str)
        ingestion_type (str):
            historical or daily
    """

    filepath = _save_csv(
        df,
        filename
    )

    s3_key = _upload_to_s3(
        filepath,
        source,
        folder
    )

    return s3_key


def cleanup_old_files(source, folder=None, keep_days=14):
    """
    Deletes Bronze files older than keep_days from S3.
    """

    if folder:
        prefix = (
            f"bronze/"
            f"{source}/"
            f"{COUNTRY}/"
            f"daily/"
            f"{folder}/"
        )
    else:
        prefix = (
            f"bronze/"
            f"{source}/"
            f"{COUNTRY}/"
            f"daily/"
        )

    response = s3.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=prefix
    )

    if "Contents" not in response:
        return

    cutoff = datetime.utcnow().date() - timedelta(days=keep_days)

    for obj in response["Contents"]:

        filename = obj["Key"].split("/")[-1]

        try:
            file_date = datetime.strptime(
                filename.replace(".csv", ""),
                "%Y%m%d"
            ).date()
        except ValueError:
            continue

        if file_date < cutoff:

            s3.delete_object(
                Bucket=S3_BUCKET,
                Key=obj["Key"]
            )

            logger.info(f"Deleted old Bronze file: {obj['Key']}")
