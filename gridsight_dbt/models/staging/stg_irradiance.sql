{{ config(materialized='view') }}

WITH irradiance AS (
  SELECT time AS timestamp,
  shortwave_radiation,
  direct_radiation,
  diffuse_radiation,
  direct_normal_irradiance
  FROM bronze_irradiance
)

SELECT * 
FROM irradiance