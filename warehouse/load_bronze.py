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

with open("warehouse/queries/bronze_weather.sql") as f:
    conn.execute(f.read())
with open("warehouse/queries/bronze_irradiance.sql") as f:
    conn.execute(f.read())
with open("warehouse/queries/bronze_generation.sql") as f:
    conn.execute(f.read())


print(conn.execute("""
SELECT COUNT(*) FROM bronze_weather;
""").fetchone()
)

print(conn.execute("""
DESCRIBE bronze_weather;
""").fetchdf()
)

print(conn.execute("""
SELECT COUNT(*) FROM bronze_irradiance;
""").fetchone()
)

print(conn.execute("""
DESCRIBE bronze_irradiance;
""").fetchdf()
)
print(conn.execute("""
SELECT COUNT(*) FROM bronze_generation;
""").fetchone()
)

print(conn.execute("""
DESCRIBE bronze_generation;
""").fetchdf()
)


conn.close()