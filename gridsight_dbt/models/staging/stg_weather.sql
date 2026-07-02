{{ config(materialized='view') }}

WITH weather AS (
  SELECT  time AS timestamp,
  temperature_2m AS temperature_c,
  CAST(relative_humidity_2m AS INT) AS relative_humidity_pct,
  precipitation AS precipitation_mm,
  CAST(cloud_cover AS INT) AS cloud_cover_pct,
  wind_speed_10m AS wind_speed_kmh,
  CAST(wind_direction_10m AS INT) AS wind_direction_deg
  FROM bronze_weather
)

SELECT * 
FROM weather