import duckdb
import os
from dotenv import load_dotenv


conn = duckdb.connect("gridsight.duckdb")

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
result = conn.execute("""
SELECT *
FROM read_csv_auto(
's3://gridsight-raw/bronze/weather/openmeteo/germany/grid_01/weather_historical_2023_01_01_2025_12_31.csv'
)
LIMIT 5
""").fetchdf()

print(result)

conn.close()