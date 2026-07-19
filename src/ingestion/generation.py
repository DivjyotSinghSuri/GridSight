import requests
import time
import pandas as pd
import xml.etree.ElementTree as ET

from requests.exceptions import RequestException

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from src.utils.config import (
    ENTSOE_API_KEY,
    ENTSOE_ENDPOINT,
    GERMANY_DOMAIN,
    DOCUMENT_TYPE,
    PROCESS_TYPE
)

from src.utils.logger import logger


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


def _generate_monthly_ranges(start_date, end_date):

    if isinstance(start_date, str):
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start = datetime.combine(start_date, datetime.min.time())

    if isinstance(end_date, str):
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.combine(end_date, datetime.min.time())

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


def _build_request(period_start, period_end):
    params = {
        "securityToken": ENTSOE_API_KEY,
        "documentType": DOCUMENT_TYPE,
        "processType": PROCESS_TYPE,
        "in_Domain": GERMANY_DOMAIN,
        "periodStart": period_start,
        "periodEnd": period_end,
    }

    return ENTSOE_ENDPOINT, params


def _request_generation(url, params):
    logger.info("Fetching generation data from ENTSO-E...")

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

            logger.info("Generation data fetched successfully.")

            return response.text

        except RequestException as e:

            if attempt == max_retries - 1:
                raise

            wait = 10 * (attempt + 1)

            logger.warning(
                f"Request failed ({e}). Retrying in {wait} seconds..."
            )

            time.sleep(wait)

    raise Exception("Maximum retries exceeded.")


def _parse_generation(xml_data):
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

            position = int(
                point.find(
                    "ns:position",
                    namespace
                ).text
            )

            quantity = float(
                point.find(
                    "ns:quantity",
                    namespace
                ).text
            )

            timestamp = start_time + timedelta(
                minutes=(position - 1) * 15
            )

            records.append({
                "timestamp": timestamp,
                "production_type": production_type,
                "generation_mw": quantity
            })

    df = pd.DataFrame(records)

    logger.info(f"Parsed {len(df)} generation records.")

    return df


def fetch_generation(start_date, end_date):
    """
    Fetches generation data from ENTSO-E.

    Returns:
        pandas.DataFrame
    """

    ranges = _generate_monthly_ranges(
    start_date,
    end_date + timedelta(days=1)
)

    monthly_dfs = []

    for period_start, period_end in ranges:

        logger.info(
            f"Processing {period_start} -> {period_end}"
        )

        url, params = _build_request(
            period_start,
            period_end
        )

        xml = _request_generation(
            url,
            params
        )

        monthly_df = _parse_generation(xml)

        monthly_dfs.append(monthly_df)

    generation_df = pd.concat(
        monthly_dfs,
        ignore_index=True
    )

    logger.info(
        f"Retrieved {len(generation_df)} total generation records."
    )

    return generation_df