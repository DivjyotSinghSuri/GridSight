{{ config(materialized='view') }}

-- Mirrors gridsight_dbt/models/staging/stg_generation.sql's filter +
-- hourly aggregation, applied to GridShield's own isolated
-- bronze_generation table.
WITH generation AS (
    SELECT * FROM {{ source('bronze', 'bronze_generation') }}
),

solar_generation AS (
    SELECT timestamp, generation_mw
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
