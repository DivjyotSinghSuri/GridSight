CREATE OR REPLACE TABLE bronze_generation AS

SELECT *
FROM read_csv_auto(
    's3://gridsight-raw/bronze/generation/entsoe/germany/historical/*.csv'
);