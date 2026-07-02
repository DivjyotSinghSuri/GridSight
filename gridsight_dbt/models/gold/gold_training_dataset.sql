{{ config(materialized='table') }}

WITH weather AS (
  SELECT *
  FROM {{ref('stg_weather')}}
),
irradiance AS (
  SELECT *
  FROM {{ref('stg_irradiance')}}
),
generation AS (
  SELECT *
  FROM {{ref('stg_generation')}}
)

SELECT g.timestamp, 
  g.solar_generation_mw, -- TARGET
  w.temperature_c, -- WEATHER
  w.relative_humidity_pct, 
  w.precipitation_mm,
  w.cloud_cover_pct,
  w.wind_speed_kmh,
  i.shortwave_radiation, -- IRRADIANCE
  i.direct_radiation,
  i.diffuse_radiation,
  i.direct_normal_irradiance,

  -- CALENDER FEATURES
  
  EXTRACT(HOUR FROM g.timestamp) AS hour,
  EXTRACT(MONTH FROM g.timestamp) AS month,
  EXTRACT(DAYOFWEEK FROM g.timestamp) AS day_of_week,
  EXTRACT(DAYOFYEAR FROM g.timestamp) AS day_of_year,
  CASE 
        WHEN EXTRACT(DAYOFWEEK FROM g.timestamp) IN (1, 7) THEN 1 
        ELSE 0 
    END AS is_weekend,
  EXTRACT(YEAR FROM g.timestamp) AS year
FROM generation AS g LEFT JOIN weather AS w 
  ON g.timestamp = w.timestamp
LEFT JOIN irradiance AS i 
  ON g.timestamp = i.timestamp
