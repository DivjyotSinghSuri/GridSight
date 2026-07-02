{{ config(materialized='view') }}

WITH irradiance AS (
  SELECT time AS timestamp,
  AVG(shortwave_radiation) AS shortwave_radiation,
  AVG(direct_radiation) AS direct_radiation,
  AVG(diffuse_radiation) AS diffuse_radiation,
  AVG(direct_normal_irradiance) AS direct_normal_irradiance
  FROM bronze_irradiance
  GROUP BY timestamp
)

SELECT * 
FROM irradiance