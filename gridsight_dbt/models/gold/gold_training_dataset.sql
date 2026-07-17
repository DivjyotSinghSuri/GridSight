{{ config(materialized='table') }}

SELECT *
FROM {{ ref('int_feature_engineering') }}
WHERE solar_generation_mw_lag_168h IS NOT NULL