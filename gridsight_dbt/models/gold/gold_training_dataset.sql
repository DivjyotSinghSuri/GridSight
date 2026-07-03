{{ config(materialized='table') }}

{% set lags = [1, 24, 168] %}

WITH weather AS (

    SELECT *
    FROM {{ ref('stg_weather') }}

),

irradiance AS (

    SELECT *
    FROM {{ ref('stg_irradiance') }}

),

generation AS (

    SELECT *
    FROM {{ ref('stg_generation') }}

),

feature_table AS (

    SELECT
        g.timestamp,
        g.solar_generation_mw,

        -- Weather
        w.temperature_c,
        w.relative_humidity_pct,
        w.precipitation_mm,
        w.cloud_cover_pct,
        w.wind_speed_kmh,

        -- Irradiance
        i.shortwave_radiation,
        i.direct_radiation,
        i.diffuse_radiation,
        i.direct_normal_irradiance,

        -- Calendar
        EXTRACT(HOUR FROM g.timestamp) AS hour,
        EXTRACT(MONTH FROM g.timestamp) AS month,
        EXTRACT(ISODOW FROM g.timestamp) AS day_of_week,
        EXTRACT(DAYOFYEAR FROM g.timestamp) AS day_of_year,

        CASE
            WHEN EXTRACT(ISODOW FROM g.timestamp) IN (6, 7) THEN 1
            ELSE 0
        END AS is_weekend,

        EXTRACT(YEAR FROM g.timestamp) AS year,

        -- Lag Features
        {% for lag in lags %}
        LAG(g.solar_generation_mw, {{ lag }})
            OVER (ORDER BY g.timestamp)
            AS solar_generation_mw_lag_{{ lag }}h{% if not loop.last %},{% endif %}
        {% endfor %}

    FROM generation AS g

    LEFT JOIN weather AS w
        ON g.timestamp = w.timestamp

    LEFT JOIN irradiance AS i
        ON g.timestamp = i.timestamp

)

SELECT *
FROM feature_table
WHERE solar_generation_mw_lag_{{ lags | max }}h IS NOT NULL