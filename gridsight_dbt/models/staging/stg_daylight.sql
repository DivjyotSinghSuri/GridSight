{{ config(materialized='view') }}

WITH daylight AS (
  SELECT CAST(time AS DATE) AS date,
    CAST(sunrise AS TIMESTAMP) AS sunrise,
    CAST(sunset AS TIMESTAMP) AS sunset,
    daylight_duration / 3600.0 AS daylight_duration_hours,
    sunshine_duration / 3600.0 AS sunshine_duration_hours
  FROM bronze_daylight)

SELECT *
FROM daylight
ORDER BY date