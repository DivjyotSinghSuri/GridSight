{{ config(materialized='table') }}

SELECT
    *
EXCLUDE (solar_generation_mw)
FROM {{ ref('int_feature_engineering') }}
WHERE solar_generation_mw_lag_168h IS NOT NULL