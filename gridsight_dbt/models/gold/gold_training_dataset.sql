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
  i.direct_normal_irradiance
FROM generation AS g LEFT JOIN weather AS w 
  ON g.timestamp = w.timestamp
LEFT JOIN irradiance AS i 
  ON g.timestamp = i.timestamp
