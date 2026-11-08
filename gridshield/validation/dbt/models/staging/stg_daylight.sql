{{ config(materialized='view') }}

-- Mirrors gridsight_dbt/models/staging/stg_daylight.sql's cast/derive
-- logic, applied to GridShield's own isolated bronze_daylight table.
WITH daylight AS (
    SELECT
        CAST(time AS DATE) AS date,
        CAST(sunrise AS TIMESTAMP) AS sunrise,
        CAST(sunset AS TIMESTAMP) AS sunset,
        daylight_duration / 3600.0 AS daylight_duration_hours,
        sunshine_duration / 3600.0 AS sunshine_duration_hours
    FROM {{ source('bronze', 'bronze_daylight') }}
)

SELECT *
FROM daylight
ORDER BY date
