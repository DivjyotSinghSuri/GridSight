{{ config(materialized='view') }}

-- Mirrors gridsight_dbt/models/staging/stg_weather.sql's aggregation
-- (Germany-wide hourly average across grid points), applied to
-- GridShield's own isolated bronze_weather table.
WITH weather AS (
    SELECT
        time AS timestamp,
        AVG(temperature_2m) AS temperature_c,
        AVG(CAST(relative_humidity_2m AS INT)) AS relative_humidity_pct,
        AVG(precipitation) AS precipitation_mm,
        AVG(CAST(cloud_cover AS INT)) AS cloud_cover_pct,
        AVG(wind_speed_10m) AS wind_speed_kmh
    FROM {{ source('bronze', 'bronze_weather') }}
    GROUP BY time
)

SELECT *
FROM weather
