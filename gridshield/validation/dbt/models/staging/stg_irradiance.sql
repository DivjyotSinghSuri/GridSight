{{ config(materialized='view') }}

-- Mirrors gridsight_dbt/models/staging/stg_irradiance.sql's aggregation
-- (Germany-wide hourly average across grid points), applied to
-- GridShield's own isolated bronze_irradiance table.
WITH irradiance AS (
    SELECT
        time AS timestamp,
        AVG(shortwave_radiation) AS shortwave_radiation,
        AVG(direct_radiation) AS direct_radiation,
        AVG(diffuse_radiation) AS diffuse_radiation,
        AVG(direct_normal_irradiance) AS direct_normal_irradiance
    FROM {{ source('bronze', 'bronze_irradiance') }}
    GROUP BY time
)

SELECT *
FROM irradiance
