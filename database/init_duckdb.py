import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

conn = duckdb.connect("gridsight.duckdb")

conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")
conn.execute(f"""
CREATE OR REPLACE SECRET gridsight_s3 (
    TYPE S3,
    KEY_ID '{AWS_ACCESS_KEY_ID}',
    SECRET '{AWS_SECRET_ACCESS_KEY}',
    REGION '{AWS_DEFAULT_REGION}'
);
""")

print("Connected successfully!")

conn.close()