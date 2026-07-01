import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

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

with open("warehouse/queries/bronze_irradiance.sql") as f:
    conn.execute(f.read())
result = conn.execute("""
DESCRIBE bronze_irradiance;
""").fetchdf()

print(result)

conn.close()