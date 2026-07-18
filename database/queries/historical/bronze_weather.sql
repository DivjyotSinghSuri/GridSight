CREATE OR REPLACE TABLE bronze_weather AS

SELECT *
FROM read_csv_auto(
    's3://gridsight-raw/bronze/weather/openmeteo/germany/*/*.csv'
);