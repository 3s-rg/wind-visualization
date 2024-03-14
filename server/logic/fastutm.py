import numba  # type: ignore
import numpy as np

K0 = 0.9996

E = 0.00669438
E2 = E * E
E3 = E2 * E
E_P2 = E / (1.0 - E)

SQRT_E = np.sqrt(1 - E)
_E = (1 - SQRT_E) / (1 + SQRT_E)
_E2 = _E * _E
_E3 = _E2 * _E
_E4 = _E3 * _E
_E5 = _E4 * _E

M1 = 1 - E / 4 - 3 * E2 / 64 - 5 * E3 / 256
# M2 = 3 * E / 8 + 3 * E2 / 32 + 45 * E3 / 1024
# M3 = 15 * E2 / 256 + 45 * E3 / 1024
# M4 = 35 * E3 / 3072

P2 = 3.0 / 2 * _E - 27.0 / 32 * _E3 + 269.0 / 512 * _E5
P3 = 21.0 / 16 * _E2 - 55.0 / 32 * _E4
P4 = 151.0 / 96 * _E3 - 417.0 / 128 * _E5
P5 = 1097.0 / 512 * _E4

R = 6378137

# ZONE_LETTERS = "CDEFGHJKLMNPQRSTUVWXX"


@numba.njit
def to_latlon(
    easting, northing, zone_number, zone_letter=None, northern=None, strict=True
):
    """
    A numba version of utm.to_latlon
    """

    def in_bounds(x, lower, upper, upper_strict=False):
        if upper_strict:
            return lower <= x < upper

        return lower <= x <= upper

    if not zone_letter and northern is None:
        raise ValueError("either zone_letter or northern needs to be set")

    elif zone_letter and northern is not None:
        raise ValueError("set either zone_letter or northern, but not both")

    if strict:
        if not in_bounds(easting, 100000, 1000000, upper_strict=True):
            raise ValueError(
                f"easting {easting} out of range (must be between 100,000 m and 999,999 m)"
            )
        if not in_bounds(northing, 0, 10000000):
            raise ValueError(
                f"northing {northing} out of range (must be between 0 m and 10,000,000 m)"
            )

    def check_valid_zone(zone_number, zone_letter):
        if not 1 <= zone_number <= 60:
            raise ValueError("zone number out of range (must be between 1 and 60)")

        if zone_letter:
            zone_letter = zone_letter.upper()

            if not "C" <= zone_letter <= "X" or zone_letter in ["I", "O"]:
                raise ValueError("zone letter out of range (must be between C and X)")

    check_valid_zone(zone_number, zone_letter)

    if zone_letter:
        zone_letter = zone_letter.upper()
        northern = zone_letter >= "N"

    x = easting - 500000
    y = northing

    if not northern:
        y -= 10000000

    m = y / K0
    mu = m / (R * M1)

    p_rad = (
        mu
        + P2 * np.sin(2 * mu)
        + P3 * np.sin(4 * mu)
        + P4 * np.sin(6 * mu)
        + P5 * np.sin(8 * mu)
    )

    p_sin = np.sin(p_rad)
    p_sin2 = p_sin * p_sin

    p_cos = np.cos(p_rad)

    p_tan = p_sin / p_cos
    p_tan2 = p_tan * p_tan
    p_tan4 = p_tan2 * p_tan2

    ep_sin = 1 - E * p_sin2
    ep_sin_sqrt = np.sqrt(1 - E * p_sin2)

    n = R / ep_sin_sqrt
    r = (1 - E) / ep_sin

    c = E_P2 * p_cos**2
    c2 = c * c

    d = x / (n * K0)
    d2 = d * d
    d3 = d2 * d
    d4 = d3 * d
    d5 = d4 * d
    d6 = d5 * d

    latitude = (
        p_rad
        - (p_tan / r)
        * (d2 / 2 - d4 / 24 * (5 + 3 * p_tan2 + 10 * c - 4 * c2 - 9 * E_P2))
        + d6 / 720 * (61 + 90 * p_tan2 + 298 * c + 45 * p_tan4 - 252 * E_P2 - 3 * c2)
    )

    longitude = (
        d
        - d3 / 6 * (1 + 2 * p_tan2 + c)
        + d5 / 120 * (5 - 2 * c + 28 * p_tan2 - 3 * c2 + 8 * E_P2 + 24 * p_tan4)
    ) / p_cos

    def mod_angle(value):
        """Returns angle in radians to be between -pi and pi"""
        return (value + np.pi) % (2 * np.pi) - np.pi

    def zone_number_to_central_longitude(zone_number):
        return (zone_number - 1) * 6 - 180 + 3

    longitude = mod_angle(
        longitude + np.radians(zone_number_to_central_longitude(zone_number))
    )

    return (np.degrees(latitude), np.degrees(longitude))
