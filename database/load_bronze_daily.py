import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = "gridsight.duckdb"

conn = duckdb.connect(DATABASE_PATH)

conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")

conn.execute(f"""
CREATE OR REPLACE SECRET gridsight_s3 (
    TYPE S3,
    KEY_ID '{os.getenv("AWS_ACCESS_KEY_ID")}',
    SECRET '{os.getenv("AWS_SECRET_ACCESS_KEY")}',
    REGION '{os.getenv("AWS_DEFAULT_REGION")}'
);
""")

queries = [
    "database/queries/daily/bronze_weather.sql",
    "database/queries/daily/bronze_irradiance.sql",
    "database/queries/daily/bronze_generation.sql",
    "database/queries/daily/bronze_daylight.sql",
]

for query in queries:
    with open(query, "r") as f:
        conn.execute(f.read())

tables = [
    "bronze_weather",
    "bronze_irradiance",
    "bronze_generation",
    "bronze_daylight",
]

for table in tables:
    count = conn.execute(
        f"SELECT COUNT(*) FROM {table};"
    ).fetchone()[0]

    print(f"{table}: {count} rows")

conn.close()