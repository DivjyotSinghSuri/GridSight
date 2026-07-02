{{ config(materialized='view') }}

WITH weather AS (
  SELECT time AS timestamp,
  AVG(temperature_2m) AS temperature_c,
  AVG(CAST(relative_humidity_2m AS INT)) AS relative_humidity_pct,
  AVG(precipitation) AS precipitation_mm,
  AVG(CAST(cloud_cover AS INT)) AS cloud_cover_pct,
  AVG(wind_speed_10m) AS wind_speed_kmh,
  FROM bronze_weather
  GROUP BY timestamp
)

SELECT * 
FROM weather