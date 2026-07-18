CREATE OR REPLACE TABLE bronze_daylight AS

SELECT *
FROM read_csv_auto(
    's3://gridsight-raw/bronze/daylight/openmeteo/germany/daily/*.csv'
);