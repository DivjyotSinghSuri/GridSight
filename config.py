COUNTRY = "germany"

TIMEZONE = "Europe/Berlin"

START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

S3_BUCKET = "gridsight-raw"

# Germany Bounding Box
MIN_LAT = 47.2
MAX_LAT = 55.1

MIN_LON = 5.9
MAX_LON = 15.0

GRID_SIZE = 5

OPEN_METEO_WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

OPEN_METEO_SOLAR_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m"
]

SOLAR_VARIABLES = [
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance"
]

ENTSOE_URL = "https://web-api.tp.entsoe.eu/api"

ENTSOE_DOMAIN = "10Y1001A1001A83F"  