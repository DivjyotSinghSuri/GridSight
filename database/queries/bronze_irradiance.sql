CREATE OR REPLACE TABLE bronze_irradiance AS

SELECT *
FROM read_csv_auto(
    's3://gridsight-raw/bronze/irradiance/openmeteo/germany/*/*.csv'
);