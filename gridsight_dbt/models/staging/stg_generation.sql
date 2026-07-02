{{ config(materialized='view') }}

WITH generation AS (
  SELECT *
  FROM bronze_generation
),

solar_generation AS (

    SELECT timestamp,
    generation_mw
    FROM generation
    WHERE production_type = 'Solar'

),

hourly_generation AS (

    SELECT
        DATE_TRUNC('hour', timestamp) AS timestamp,
        AVG(generation_mw) AS solar_generation_mw
    FROM solar_generation
    GROUP BY DATE_TRUNC('hour', timestamp)
)

SELECT *
FROM hourly_generation
ORDER BY timestamp