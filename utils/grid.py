import numpy as np

from config import (
    MIN_LAT,
    MAX_LAT,
    MIN_LON,
    MAX_LON,
    GRID_SIZE
)


def generate_grid():
    """
    Generate evenly spaced latitude/longitude grid points.

    Returns:
        list[tuple]:
        [
            ("grid_01", lat, lon),
            ...
        ]
    """

    latitudes = np.linspace(MIN_LAT, MAX_LAT, GRID_SIZE)
    longitudes = np.linspace(MIN_LON, MAX_LON, GRID_SIZE)

    grid_points = []

    count = 1

    for lat in latitudes:
        for lon in longitudes:

            grid_points.append(
                (
                    f"grid_{count:02d}",
                    round(float(lat), 4),
                    round(float(lon), 4)
                )
            )

            count += 1

    return grid_points