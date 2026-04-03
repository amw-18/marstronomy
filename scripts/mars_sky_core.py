"""Shared helpers for the Mars sky proof-of-concept scripts."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


CATALOG_DEFAULT = "bsc5.json"
DEFAULT_UTC = "2026-04-04T00:00:00Z"
OLYMPUS_MONS_LAT_DEG = 18.65
OLYMPUS_MONS_LON_EAST_DEG = 226.2

TT_MINUS_UTC_SECONDS_DEFAULT = 69.184

MARS_POLE_RA_0_DEG = 317.68143
MARS_POLE_RA_RATE_DEG_PER_CENTURY = -0.1061
MARS_POLE_DEC_0_DEG = 52.88650
MARS_POLE_DEC_RATE_DEG_PER_CENTURY = -0.0609
MARS_PM_0_DEG = 176.630
MARS_PM_RATE_DEG_PER_DAY = 350.89198226
JD_J2000 = 2451545.0
JULIAN_CENTURY_DAYS = 36525.0

MARS_MEAN_RADIUS_KM = 3389.5
MARS_SOL_DURATION_DAYS = 1.0274912517
MARS_SOL_DURATION_SECONDS = MARS_SOL_DURATION_DAYS * 86400.0
MARS_SIDEREAL_DAY_DAYS = 360.0 / MARS_PM_RATE_DEG_PER_DAY
MARS_SIDEREAL_DAY_SECONDS = MARS_SIDEREAL_DAY_DAYS * 86400.0
MARS_MEAN_HELIOCENTRIC_DISTANCE_AU = 1.52367934

MARS24_PBS_TERMS: Sequence[Tuple[float, float, float]] = (
    (0.0071, 2.2353, 49.409),
    (0.0057, 2.7543, 168.173),
    (0.0039, 1.1177, 191.837),
    (0.0037, 15.7866, 21.736),
    (0.0021, 2.1354, 15.704),
    (0.0020, 2.4694, 95.528),
    (0.0018, 32.8493, 49.095),
)

DEFAULT_STAR_LABEL_COUNT = 18
DEFAULT_TIMELINE_FRAME_COUNT = 289
DEFAULT_KEYFRAME_COUNT = 6
DEFAULT_TIMELINE_DURATION_SOLS = 2.0

SUN_COLOR = "#ffd54a"
PHOBOS_COLOR = "#ddd7cb"
DEIMOS_COLOR = "#aeb9d1"

LEAP_SECOND_TABLE: Sequence[Tuple[str, float]] = (
    ("1972-01-01T00:00:00Z", 42.184),
    ("1972-07-01T00:00:00Z", 43.184),
    ("1973-01-01T00:00:00Z", 44.184),
    ("1974-01-01T00:00:00Z", 45.184),
    ("1975-01-01T00:00:00Z", 46.184),
    ("1976-01-01T00:00:00Z", 47.184),
    ("1977-01-01T00:00:00Z", 48.184),
    ("1978-01-01T00:00:00Z", 49.184),
    ("1979-01-01T00:00:00Z", 50.184),
    ("1980-01-01T00:00:00Z", 51.184),
    ("1981-07-01T00:00:00Z", 52.184),
    ("1982-07-01T00:00:00Z", 53.184),
    ("1983-07-01T00:00:00Z", 54.184),
    ("1985-07-01T00:00:00Z", 55.184),
    ("1988-01-01T00:00:00Z", 56.184),
    ("1990-01-01T00:00:00Z", 57.184),
    ("1991-01-01T00:00:00Z", 58.184),
    ("1992-07-01T00:00:00Z", 59.184),
    ("1993-07-01T00:00:00Z", 60.184),
    ("1994-07-01T00:00:00Z", 61.184),
    ("1996-01-01T00:00:00Z", 62.184),
    ("1997-07-01T00:00:00Z", 63.184),
    ("1999-01-01T00:00:00Z", 64.184),
    ("2006-01-01T00:00:00Z", 65.184),
    ("2009-01-01T00:00:00Z", 66.184),
    ("2012-07-01T00:00:00Z", 67.184),
    ("2015-07-01T00:00:00Z", 68.184),
    ("2017-01-01T00:00:00Z", 69.184),
)


@dataclass(frozen=True)
class Star:
    hr: Optional[int]
    name: str
    ra_deg: float
    dec_deg: float
    vmag: float
    kelvin: Optional[float]


@dataclass(frozen=True)
class VisibleStar:
    hr: Optional[int]
    name: str
    ra_deg: float
    dec_deg: float
    az_deg: float
    alt_deg: float
    vmag: float
    kelvin: Optional[float]
    size_px: float
    rgb: str


@dataclass(frozen=True)
class Site:
    name: str
    latitude_deg: float
    longitude_east_deg: float
    radius_km: float = MARS_MEAN_RADIUS_KM

    @property
    def longitude_west_deg(self) -> float:
        return wrap_degrees(360.0 - self.longitude_east_deg)


@dataclass(frozen=True)
class MarsSolarData:
    jd_tt: float
    delta_j2000_days: float
    mean_anomaly_deg: float
    alpha_fms_deg: float
    pbs_deg: float
    equation_of_center_deg: float
    ls_deg: float
    eot_deg: float
    mst_hours: float
    lmst_hours: float
    ltst_hours: float
    subsolar_longitude_west_deg: float
    subsolar_longitude_east_deg: float
    solar_declination_deg: float
    heliocentric_distance_au: float


@dataclass(frozen=True)
class MoonModel:
    kind: str
    name: str
    orbital_radius_km: float
    orbital_period_days: float
    phase_at_j2000_deg: float
    color: str
    symbol_size_px: float

    @property
    def relative_rate_deg_per_day(self) -> float:
        return (360.0 / self.orbital_period_days) - MARS_PM_RATE_DEG_PER_DAY


@dataclass(frozen=True)
class MovingBody:
    kind: str
    name: str
    alt_deg: float
    az_deg: float
    visible: bool
    symbol_size_px: float
    color: str
    distance_km: Optional[float] = None
    distance_au: Optional[float] = None


PHOBOS_MODEL = MoonModel(
    kind="phobos",
    name="Phobos",
    orbital_radius_km=9375.0,
    orbital_period_days=0.3187,
    phase_at_j2000_deg=189.7,
    color=PHOBOS_COLOR,
    symbol_size_px=8.5,
)

DEIMOS_MODEL = MoonModel(
    kind="deimos",
    name="Deimos",
    orbital_radius_km=23457.0,
    orbital_period_days=1.2625,
    phase_at_j2000_deg=205.0,
    color=DEIMOS_COLOR,
    symbol_size_px=5.4,
)


def default_site() -> Site:
    return Site(
        name="Olympus Mons",
        latitude_deg=OLYMPUS_MONS_LAT_DEG,
        longitude_east_deg=OLYMPUS_MONS_LON_EAST_DEG,
    )


def parse_iso_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def datetime_to_jd_utc(dt: datetime) -> float:
    return 2440587.5 + (dt.timestamp() / 86400.0)


def tt_minus_utc_seconds(dt_utc: datetime) -> float:
    for threshold_str, value in reversed(LEAP_SECOND_TABLE):
        if dt_utc >= parse_iso_utc(threshold_str):
            return value
    return TT_MINUS_UTC_SECONDS_DEFAULT


def datetime_to_jd_tt(dt_utc: datetime) -> float:
    jd_utc = datetime_to_jd_utc(dt_utc)
    return jd_utc + (tt_minus_utc_seconds(dt_utc) / 86400.0)


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def wrap_degrees(value: float) -> float:
    return value % 360.0


def wrap_degrees_signed(value: float) -> float:
    wrapped = wrap_degrees(value)
    if wrapped >= 180.0:
        wrapped -= 360.0
    return wrapped


def wrap_hours(value: float) -> float:
    return value % 24.0


def deg_to_rad(value: float) -> float:
    return math.radians(value)


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    )


def vector_norm(vector: Sequence[float]) -> float:
    return math.sqrt(dot(vector, vector))


def normalize_vector(vector: Sequence[float]) -> Tuple[float, float, float]:
    length = vector_norm(vector)
    if length == 0.0:
        raise ValueError("Cannot normalize a zero-length vector.")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def scale_vector(vector: Sequence[float], scale: float) -> Tuple[float, float, float]:
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def subtract_vectors(
    a: Sequence[float], b: Sequence[float]
) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def rotate_about_axis(
    vector: Sequence[float], axis_unit: Sequence[float], angle_deg: float
) -> Tuple[float, float, float]:
    angle = deg_to_rad(angle_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    axis_dot = dot(axis_unit, vector)
    axis_cross = cross(axis_unit, vector)
    return (
        vector[0] * cos_a + axis_cross[0] * sin_a + axis_unit[0] * axis_dot * (1.0 - cos_a),
        vector[1] * cos_a + axis_cross[1] * sin_a + axis_unit[1] * axis_dot * (1.0 - cos_a),
        vector[2] * cos_a + axis_cross[2] * sin_a + axis_unit[2] * axis_dot * (1.0 - cos_a),
    )


def vector_from_ra_dec(ra_deg: float, dec_deg: float) -> Tuple[float, float, float]:
    ra = deg_to_rad(ra_deg)
    dec = deg_to_rad(dec_deg)
    cos_dec = math.cos(dec)
    return (
        cos_dec * math.cos(ra),
        cos_dec * math.sin(ra),
        math.sin(dec),
    )


def body_vector_from_lat_lon(
    lat_deg: float, lon_east_deg: float
) -> Tuple[float, float, float]:
    lat = deg_to_rad(lat_deg)
    lon = deg_to_rad(lon_east_deg)
    return (
        math.cos(lat) * math.cos(lon),
        math.cos(lat) * math.sin(lon),
        math.sin(lat),
    )


def local_basis(
    lat_deg: float, lon_east_deg: float
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
    lat = deg_to_rad(lat_deg)
    lon = deg_to_rad(lon_east_deg)
    up = (
        math.cos(lat) * math.cos(lon),
        math.cos(lat) * math.sin(lon),
        math.sin(lat),
    )
    east = (-math.sin(lon), math.cos(lon), 0.0)
    north = (
        -math.sin(lat) * math.cos(lon),
        -math.sin(lat) * math.sin(lon),
        math.cos(lat),
    )
    return east, north, up


def vector_to_alt_az(
    vector_body: Sequence[float],
    east: Sequence[float],
    north: Sequence[float],
    up: Sequence[float],
) -> Tuple[float, float]:
    unit = normalize_vector(vector_body)
    e_comp = dot(unit, east)
    n_comp = dot(unit, north)
    u_comp = max(-1.0, min(1.0, dot(unit, up)))
    alt_deg = math.degrees(math.asin(u_comp))
    az_deg = wrap_degrees(math.degrees(math.atan2(e_comp, n_comp)))
    return alt_deg, az_deg


def direction_to_alt_az(
    direction_body: Sequence[float], lat_deg: float, lon_east_deg: float
) -> Tuple[float, float]:
    east, north, up = local_basis(lat_deg, lon_east_deg)
    return vector_to_alt_az(direction_body, east, north, up)


def observer_position_body(
    lat_deg: float,
    lon_east_deg: float,
    radius_km: float = MARS_MEAN_RADIUS_KM,
) -> Tuple[float, float, float]:
    return scale_vector(body_vector_from_lat_lon(lat_deg, lon_east_deg), radius_km)


def topocentric_alt_az_from_position(
    position_body_km: Sequence[float],
    lat_deg: float,
    lon_east_deg: float,
    observer_radius_km: float = MARS_MEAN_RADIUS_KM,
) -> Tuple[float, float, float]:
    observer = observer_position_body(lat_deg, lon_east_deg, observer_radius_km)
    topocentric = subtract_vectors(position_body_km, observer)
    east, north, up = local_basis(lat_deg, lon_east_deg)
    alt_deg, az_deg = vector_to_alt_az(topocentric, east, north, up)
    return alt_deg, az_deg, vector_norm(topocentric)


def mars_orientation(jd_tt: float) -> Tuple[float, float, float]:
    delta_days = jd_tt - JD_J2000
    centuries = delta_days / JULIAN_CENTURY_DAYS
    pole_ra_deg = MARS_POLE_RA_0_DEG + (MARS_POLE_RA_RATE_DEG_PER_CENTURY * centuries)
    pole_dec_deg = MARS_POLE_DEC_0_DEG + (MARS_POLE_DEC_RATE_DEG_PER_CENTURY * centuries)
    prime_meridian_deg = wrap_degrees(MARS_PM_0_DEG + (MARS_PM_RATE_DEG_PER_DAY * delta_days))
    return pole_ra_deg, pole_dec_deg, prime_meridian_deg


def mars_body_basis(
    pole_ra_deg: float, pole_dec_deg: float, prime_meridian_deg: float
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
    pole = vector_from_ra_dec(pole_ra_deg, pole_dec_deg)
    pole_ra = deg_to_rad(pole_ra_deg)
    ascending_node = (-math.sin(pole_ra), math.cos(pole_ra), 0.0)
    x_body = rotate_about_axis(ascending_node, pole, prime_meridian_deg)
    y_body = cross(pole, x_body)
    return x_body, y_body, pole


def inertial_to_body(
    vector_inertial: Sequence[float],
    x_body: Sequence[float],
    y_body: Sequence[float],
    z_body: Sequence[float],
) -> Tuple[float, float, float]:
    return (
        dot(vector_inertial, x_body),
        dot(vector_inertial, y_body),
        dot(vector_inertial, z_body),
    )


def unwrap_catalog_root(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    if isinstance(raw, dict):
        preferred_keys = ("data", "stars", "items", "catalog", "entries")
        for key in preferred_keys:
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        for value in raw.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return [item for item in value if isinstance(item, dict)]

    raise ValueError("Could not locate a list of star records in the catalog JSON.")


def load_catalog(path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    records = unwrap_catalog_root(raw)
    if not records:
        raise ValueError("Catalog loaded, but no star records were found.")
    sample_keys = sorted(records[0].keys())
    return records, sample_keys


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def maybe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_ra_to_deg(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric * 15.0 if 0.0 <= numeric <= 24.0 else numeric

    text = clean_text(value)
    if not text:
        return None

    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if not matches:
        return None

    parts = [float(match) for match in matches]
    if any(marker in text.lower() for marker in ("h", "m", "s")) or len(parts) >= 2:
        hours = parts[0]
        minutes = parts[1] if len(parts) > 1 else 0.0
        seconds = parts[2] if len(parts) > 2 else 0.0
        return 15.0 * (hours + (minutes / 60.0) + (seconds / 3600.0))

    numeric = parts[0]
    return numeric * 15.0 if 0.0 <= numeric <= 24.0 else numeric


def parse_dec_to_deg(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(value)
    if not text:
        return None

    normalized = (
        text.replace("−", "-")
        .replace("–", "-")
        .replace("′", "'")
        .replace("″", '"')
    )
    sign = -1.0 if normalized.startswith("-") else 1.0
    matches = re.findall(r"\d+(?:\.\d+)?", normalized)
    if not matches:
        return None

    parts = [float(match) for match in matches]
    degrees = parts[0]
    minutes = parts[1] if len(parts) > 1 else 0.0
    seconds = parts[2] if len(parts) > 2 else 0.0
    return sign * (degrees + (minutes / 60.0) + (seconds / 3600.0))


def build_star_name(record: Dict[str, Any]) -> str:
    common = clean_text(record.get("Common") or record.get("N"))
    if common:
        return common

    constellation = clean_text(record.get("Constellation") or record.get("C"))

    bayer = clean_text(record.get("BayerF") or record.get("Bayer") or record.get("B"))
    if bayer and constellation and constellation.lower() not in bayer.lower():
        return f"{bayer} {constellation}"
    if bayer:
        return bayer

    flamsteed = clean_text(
        record.get("FlamsteedF") or record.get("Flamsteed") or record.get("F")
    )
    if flamsteed and constellation and constellation.lower() not in flamsteed.lower():
        return f"{flamsteed} {constellation}"
    if flamsteed:
        return flamsteed

    hr_value = clean_text(record.get("HR"))
    if hr_value:
        return f"HR {hr_value}"

    return "Unnamed"


def normalize_star(record: Dict[str, Any]) -> Optional[Star]:
    ra_deg = parse_ra_to_deg(record.get("RA") or record.get("ra"))
    dec_deg = parse_dec_to_deg(record.get("Dec") or record.get("dec"))
    vmag = maybe_float(
        record.get("V")
        or record.get("Vmag")
        or record.get("vmag")
        or record.get("mag")
    )
    if ra_deg is None or dec_deg is None or vmag is None:
        return None

    hr_value = maybe_float(record.get("HR"))
    hr = int(hr_value) if hr_value is not None else None
    kelvin = maybe_float(record.get("K") or record.get("kelvin"))
    return Star(
        hr=hr,
        name=build_star_name(record),
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        vmag=vmag,
        kelvin=kelvin,
    )


def load_normalized_catalog(path: str) -> Tuple[List[Star], List[str], int]:
    records, sample_keys = load_catalog(path)
    stars = [star for star in (normalize_star(record) for record in records) if star]
    return stars, sample_keys, len(records)


def marker_size_for_mag(vmag: float) -> float:
    size = 8.0 * math.pow(10.0, -0.18 * (vmag + 1.0))
    return max(0.8, min(size, 7.5))


def clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def kelvin_to_rgb(kelvin: Optional[float]) -> str:
    if kelvin is None:
        return "#f5f7ff"

    temp = max(1000.0, min(40000.0, kelvin)) / 100.0
    if temp <= 66.0:
        red = 255.0
        green = 99.4708025861 * math.log(temp) - 161.1195681661
        if temp <= 19.0:
            blue = 0.0
        else:
            blue = 138.5177312231 * math.log(temp - 10.0) - 305.0447927307
    else:
        red = 329.698727446 * math.pow(temp - 60.0, -0.1332047592)
        green = 288.1221695283 * math.pow(temp - 60.0, -0.0755148492)
        blue = 255.0

    return "#{:02x}{:02x}{:02x}".format(
        clamp_channel(red),
        clamp_channel(green),
        clamp_channel(blue),
    )


def build_visible_stars(
    stars: Iterable[Star],
    lat_deg: float,
    lon_east_deg: float,
    jd_tt: float,
    mag_limit: float,
) -> List[VisibleStar]:
    pole_ra_deg, pole_dec_deg, prime_meridian_deg = mars_orientation(jd_tt)
    x_body, y_body, z_body = mars_body_basis(pole_ra_deg, pole_dec_deg, prime_meridian_deg)
    east, north, up = local_basis(lat_deg, lon_east_deg)

    visible: List[VisibleStar] = []
    for star in stars:
        if star.vmag > mag_limit:
            continue
        inertial = vector_from_ra_dec(star.ra_deg, star.dec_deg)
        body = inertial_to_body(inertial, x_body, y_body, z_body)
        alt_deg, az_deg = vector_to_alt_az(body, east, north, up)
        if alt_deg <= 0.0:
            continue
        visible.append(
            VisibleStar(
                hr=star.hr,
                name=star.name,
                ra_deg=star.ra_deg,
                dec_deg=star.dec_deg,
                az_deg=az_deg,
                alt_deg=alt_deg,
                vmag=star.vmag,
                kelvin=star.kelvin,
                size_px=marker_size_for_mag(star.vmag),
                rgb=kelvin_to_rgb(star.kelvin),
            )
        )

    visible.sort(key=lambda star: (star.vmag, -star.alt_deg, star.name))
    return visible


def mars_solar_data(jd_tt: float, longitude_east_deg: float) -> MarsSolarData:
    delta_days = jd_tt - JD_J2000
    mean_anomaly_deg = wrap_degrees(19.3871 + (0.52402073 * delta_days))
    alpha_fms_deg = wrap_degrees(270.3871 + (0.524038496 * delta_days))

    pbs_deg = 0.0
    for amplitude, tau, phi in MARS24_PBS_TERMS:
        argument_deg = (0.985626 * delta_days / tau) + phi
        pbs_deg += amplitude * math.cos(deg_to_rad(argument_deg))

    mean_anomaly_rad = deg_to_rad(mean_anomaly_deg)
    equation_of_center_deg = (
        (10.691 + (3.0e-7 * delta_days)) * math.sin(mean_anomaly_rad)
        + 0.623 * math.sin(2.0 * mean_anomaly_rad)
        + 0.050 * math.sin(3.0 * mean_anomaly_rad)
        + 0.005 * math.sin(4.0 * mean_anomaly_rad)
        + 0.0005 * math.sin(5.0 * mean_anomaly_rad)
        + pbs_deg
    )
    ls_deg = wrap_degrees(alpha_fms_deg + equation_of_center_deg)
    ls_rad = deg_to_rad(ls_deg)

    eot_deg = wrap_degrees_signed(
        (2.861 * math.sin(2.0 * ls_rad))
        - (0.071 * math.sin(4.0 * ls_rad))
        + (0.002 * math.sin(6.0 * ls_rad))
        - equation_of_center_deg
    )

    mst_hours = wrap_hours(
        24.0
        * (((jd_tt - 2451549.5) / MARS_SOL_DURATION_DAYS) + 44796.0 - 0.0009626)
    )

    longitude_west_deg = wrap_degrees(360.0 - longitude_east_deg)
    lmst_hours = wrap_hours(mst_hours - (longitude_west_deg / 15.0))
    ltst_hours = wrap_hours(lmst_hours + (eot_deg / 15.0))

    subsolar_longitude_west_deg = wrap_degrees((mst_hours * 15.0) + eot_deg + 180.0)
    subsolar_longitude_east_deg = wrap_degrees(360.0 - subsolar_longitude_west_deg)

    solar_declination_deg = math.degrees(math.asin(0.42565 * math.sin(ls_rad))) + (
        0.25 * math.sin(ls_rad)
    )

    heliocentric_distance_au = MARS_MEAN_HELIOCENTRIC_DISTANCE_AU * (
        1.00436
        - (0.09309 * math.cos(mean_anomaly_rad))
        - (0.004336 * math.cos(2.0 * mean_anomaly_rad))
        - (0.00031 * math.cos(3.0 * mean_anomaly_rad))
        - (0.00003 * math.cos(4.0 * mean_anomaly_rad))
    )

    return MarsSolarData(
        jd_tt=jd_tt,
        delta_j2000_days=delta_days,
        mean_anomaly_deg=mean_anomaly_deg,
        alpha_fms_deg=alpha_fms_deg,
        pbs_deg=pbs_deg,
        equation_of_center_deg=equation_of_center_deg,
        ls_deg=ls_deg,
        eot_deg=eot_deg,
        mst_hours=mst_hours,
        lmst_hours=lmst_hours,
        ltst_hours=ltst_hours,
        subsolar_longitude_west_deg=subsolar_longitude_west_deg,
        subsolar_longitude_east_deg=subsolar_longitude_east_deg,
        solar_declination_deg=solar_declination_deg,
        heliocentric_distance_au=heliocentric_distance_au,
    )


def sun_direction_body(solar_data: MarsSolarData) -> Tuple[float, float, float]:
    return body_vector_from_lat_lon(
        solar_data.solar_declination_deg,
        solar_data.subsolar_longitude_east_deg,
    )


def sun_symbol_size_px(heliocentric_distance_au: float) -> float:
    size = 20.0 * (MARS_MEAN_HELIOCENTRIC_DISTANCE_AU / heliocentric_distance_au)
    return max(17.0, min(size, 23.5))


def build_sun_body(
    solar_data: MarsSolarData, lat_deg: float, lon_east_deg: float
) -> MovingBody:
    direction = sun_direction_body(solar_data)
    alt_deg, az_deg = direction_to_alt_az(direction, lat_deg, lon_east_deg)
    return MovingBody(
        kind="sun",
        name="Sun",
        alt_deg=alt_deg,
        az_deg=az_deg,
        visible=alt_deg > 0.0,
        symbol_size_px=sun_symbol_size_px(solar_data.heliocentric_distance_au),
        color=SUN_COLOR,
        distance_au=solar_data.heliocentric_distance_au,
    )


def moon_body_position(model: MoonModel, jd_tt: float) -> Tuple[Tuple[float, float, float], float]:
    delta_days = jd_tt - JD_J2000
    lon_east_deg = wrap_degrees(model.phase_at_j2000_deg + (model.relative_rate_deg_per_day * delta_days))
    position = scale_vector(body_vector_from_lat_lon(0.0, lon_east_deg), model.orbital_radius_km)
    return position, lon_east_deg


def build_moon_body(
    model: MoonModel,
    jd_tt: float,
    lat_deg: float,
    lon_east_deg: float,
    observer_radius_km: float = MARS_MEAN_RADIUS_KM,
) -> MovingBody:
    position_body, _ = moon_body_position(model, jd_tt)
    alt_deg, az_deg, distance_km = topocentric_alt_az_from_position(
        position_body,
        lat_deg,
        lon_east_deg,
        observer_radius_km=observer_radius_km,
    )
    return MovingBody(
        kind=model.kind,
        name=model.name,
        alt_deg=alt_deg,
        az_deg=az_deg,
        visible=alt_deg > 0.0,
        symbol_size_px=model.symbol_size_px,
        color=model.color,
        distance_km=distance_km,
    )


def star_opacity_from_sun_altitude(sun_alt_deg: float) -> float:
    if sun_alt_deg <= -18.0:
        return 1.0
    if sun_alt_deg >= 12.0:
        return 0.08
    t = (sun_alt_deg + 18.0) / 30.0
    t = max(0.0, min(1.0, t))
    eased = t * t * (3.0 - (2.0 * t))
    return 1.0 - (0.92 * eased)


def moon_opacity_from_sun_altitude(sun_alt_deg: float) -> float:
    if sun_alt_deg <= -18.0:
        return 1.0
    if sun_alt_deg >= 12.0:
        return 0.4
    t = (sun_alt_deg + 18.0) / 30.0
    t = max(0.0, min(1.0, t))
    eased = t * t * (3.0 - (2.0 * t))
    return 1.0 - (0.6 * eased)


def moving_body_to_dict(body: MovingBody) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": body.kind,
        "name": body.name,
        "alt_deg": round(body.alt_deg, 6),
        "az_deg": round(body.az_deg, 6),
        "visible": body.visible,
        "symbol_size_px": round(body.symbol_size_px, 3),
        "color": body.color,
    }
    if body.distance_km is not None:
        payload["distance_km"] = round(body.distance_km, 3)
    if body.distance_au is not None:
        payload["distance_au"] = round(body.distance_au, 6)
    return payload


def scene_bodies_for_time(
    dt_utc: datetime,
    site: Site,
) -> Tuple[MarsSolarData, MovingBody, MovingBody, MovingBody]:
    jd_tt = datetime_to_jd_tt(dt_utc)
    solar_data = mars_solar_data(jd_tt, site.longitude_east_deg)
    sun = build_sun_body(solar_data, site.latitude_deg, site.longitude_east_deg)
    phobos = build_moon_body(
        PHOBOS_MODEL,
        jd_tt,
        site.latitude_deg,
        site.longitude_east_deg,
        observer_radius_km=site.radius_km,
    )
    deimos = build_moon_body(
        DEIMOS_MODEL,
        jd_tt,
        site.latitude_deg,
        site.longitude_east_deg,
        observer_radius_km=site.radius_km,
    )
    return solar_data, sun, phobos, deimos


def timeline_frame(
    dt_utc: datetime,
    site: Site,
) -> Dict[str, Any]:
    _, sun, phobos, deimos = scene_bodies_for_time(dt_utc, site)
    star_opacity = star_opacity_from_sun_altitude(sun.alt_deg)
    return {
        "utc": utc_isoformat(dt_utc),
        "sun_alt_deg": round(sun.alt_deg, 6),
        "sun_az_deg": round(sun.az_deg, 6),
        "sun_visible": sun.visible,
        "star_opacity": round(star_opacity, 4),
        "moving_bodies": [
            moving_body_to_dict(sun),
            moving_body_to_dict(phobos),
            moving_body_to_dict(deimos),
        ],
    }


def generate_frame_times(
    start_utc: datetime,
    duration_sols: float,
    frame_count: int,
) -> List[datetime]:
    if frame_count <= 0:
        raise ValueError("frame_count must be positive.")
    if frame_count == 1:
        return [start_utc]
    total_seconds = duration_sols * MARS_SOL_DURATION_SECONDS
    step_seconds = total_seconds / float(frame_count - 1)
    return [
        start_utc + timedelta(seconds=(step_seconds * index))
        for index in range(frame_count)
    ]


def build_scene_timeline(
    start_utc: datetime,
    site: Site,
    duration_sols: float = DEFAULT_TIMELINE_DURATION_SOLS,
    frame_count: int = DEFAULT_TIMELINE_FRAME_COUNT,
) -> List[Dict[str, Any]]:
    times = generate_frame_times(start_utc, duration_sols, frame_count)
    return [timeline_frame(dt_utc, site) for dt_utc in times]


def build_keyframe_indices(frame_count: int, keyframe_count: int) -> List[int]:
    if frame_count <= 0:
        return []
    if keyframe_count <= 1:
        return [0]

    keyframe_count = min(frame_count, keyframe_count)
    step = (frame_count - 1) / float(keyframe_count - 1)
    indices: List[int] = []
    last = -1
    for index in range(keyframe_count):
        candidate = int(round(index * step))
        if candidate <= last:
            candidate = min(frame_count - 1, last + 1)
        indices.append(candidate)
        last = candidate
    return indices


def approximation_notes() -> List[str]:
    return [
        "Sun uses NASA Mars24 seasonal and time-of-day formulas.",
        "Phobos and Deimos use circular, equatorial Mars-body-frame motion with fixed J2000 phase seeds.",
        "Moon positions are topocentric, using observer-to-moon vectors instead of infinite-distance directions.",
        "No SPICE kernels, eclipses, phases, transits, refraction, or photometric atmosphere are modeled.",
    ]


def site_payload(site: Site) -> Dict[str, Any]:
    return {
        "name": site.name,
        "latitude_deg": site.latitude_deg,
        "longitude_east_deg": site.longitude_east_deg,
        "longitude_west_deg": site.longitude_west_deg,
        "radius_km": site.radius_km,
    }


def write_json(path: str, payload: Dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def write_visible_star_snapshot(
    output_path: str,
    visible_stars: Sequence[VisibleStar],
    utc_text: str,
    site: Site,
    sample_keys: Sequence[str],
) -> None:
    payload = {
        "site": site_payload(site),
        "observation_utc": utc_text,
        "catalog_schema_hint": list(sample_keys),
        "visible_count": len(visible_stars),
        "stars": [
            {
                "hr": star.hr,
                "name": star.name,
                "ra_deg": round(star.ra_deg, 6),
                "dec_deg": round(star.dec_deg, 6),
                "az_deg": round(star.az_deg, 6),
                "alt_deg": round(star.alt_deg, 6),
                "vmag": star.vmag,
                "kelvin": star.kelvin,
                "size_px": round(star.size_px, 3),
                "rgb": star.rgb,
            }
            for star in visible_stars
        ],
    }
    write_json(output_path, payload)


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_sky_svg(
    output_path: str,
    visible_stars: Sequence[VisibleStar],
    utc_text: str,
    site: Site,
    title: str,
    subtitle: Optional[str] = None,
    star_opacity: float = 1.0,
    label_count: int = DEFAULT_STAR_LABEL_COUNT,
    moving_bodies: Optional[Sequence[MovingBody]] = None,
    sun_altitude_deg: Optional[float] = None,
) -> None:
    ensure_parent_dir(output_path)

    width = 1200
    height = 1200
    cx = width / 2.0
    cy = height / 2.0
    radius = 500.0
    rings = [15, 30, 45, 60, 75]
    cardinals = [("N", 0.0), ("E", 90.0), ("S", 180.0), ("W", 270.0)]

    moving_bodies = list(moving_bodies or [])
    subtitle_text = subtitle or (
        f"{utc_text} | lat {site.latitude_deg:.2f} | lonE {site.longitude_east_deg:.2f}"
    )

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        "<defs>",
        (
            '<radialGradient id="bg" cx="50%" cy="50%" r="60%">'
            '<stop offset="0%" stop-color="#0e1527"/>'
            '<stop offset="70%" stop-color="#070b14"/>'
            '<stop offset="100%" stop-color="#02040a"/>'
            "</radialGradient>"
        ),
        (
            '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
            '<feGaussianBlur stdDeviation="2" result="blur"/>'
            '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
            "</filter>"
        ),
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>',
        (
            f'<text x="{cx}" y="72" fill="#eef4ff" font-size="28" '
            'font-family="Menlo, Consolas, monospace" text-anchor="middle">'
            f"{svg_escape(title)}"
            "</text>"
        ),
        (
            f'<text x="{cx}" y="106" fill="#a9b7d9" font-size="18" '
            'font-family="Menlo, Consolas, monospace" text-anchor="middle">'
            f"{svg_escape(subtitle_text)}"
            "</text>"
        ),
        (
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
            'stroke="#5d6b8c" stroke-width="2"/>'
        ),
    ]

    for alt in rings:
        ring_radius = radius * ((90.0 - alt) / 90.0)
        lines.append(
            f'<circle cx="{cx}" cy="{cy}" r="{ring_radius:.2f}" fill="none" '
            'stroke="#24314c" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{cx + 8}" y="{cy - ring_radius - 6:.2f}" fill="#5f7198" '
            'font-size="14" font-family="Menlo, Consolas, monospace">'
            f"{alt}°"
            "</text>"
        )

    for label, az_deg in cardinals:
        az = deg_to_rad(az_deg)
        x = cx + (radius + 24.0) * math.sin(az)
        y = cy - (radius + 24.0) * math.cos(az)
        lines.append(
            f'<line x1="{cx}" y1="{cy}" x2="{cx + radius * math.sin(az):.2f}" '
            f'y2="{cy - radius * math.cos(az):.2f}" stroke="#182339" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{y:.2f}" fill="#d7e3ff" font-size="22" '
            'font-family="Menlo, Consolas, monospace" text-anchor="middle" '
            'dominant-baseline="middle">'
            f"{label}"
            "</text>"
        )

    labeled = set()
    for star in visible_stars[:label_count]:
        if star.name != "Unnamed":
            labeled.add((star.hr, star.name))

    global_star_opacity = max(0.0, min(1.0, star_opacity))
    for star in visible_stars:
        r = radius * ((90.0 - star.alt_deg) / 90.0)
        az = deg_to_rad(star.az_deg)
        x = cx + r * math.sin(az)
        y = cy - r * math.cos(az)
        base_opacity = min(1.0, max(0.35, 1.1 - (star.vmag / 9.0)))
        opacity = base_opacity * global_star_opacity
        lines.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{star.size_px:.2f}" '
            f'fill="{star.rgb}" opacity="{opacity:.3f}" filter="url(#glow)"/>'
        )
        if (star.hr, star.name) in labeled and opacity >= 0.18:
            lines.append(
                f'<text x="{x + 10.0:.2f}" y="{y - 10.0:.2f}" fill="#c9d7f4" '
                'font-size="15" font-family="Menlo, Consolas, monospace">'
                f"{svg_escape(star.name)}"
                "</text>"
            )

    moon_opacity = moon_opacity_from_sun_altitude(sun_altitude_deg or -30.0)
    for body in moving_bodies:
        if not body.visible:
            continue
        r = radius * ((90.0 - body.alt_deg) / 90.0)
        az = deg_to_rad(body.az_deg)
        x = cx + r * math.sin(az)
        y = cy - r * math.cos(az)
        opacity = 1.0 if body.kind == "sun" else moon_opacity
        stroke = "#fff4d0" if body.kind == "sun" else "#dbe2ef"
        glow_radius = body.symbol_size_px * (1.7 if body.kind == "sun" else 1.25)
        lines.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{glow_radius:.2f}" '
            f'fill="{body.color}" opacity="{0.16 if body.kind == "sun" else 0.08:.3f}" '
            'filter="url(#glow)"/>'
        )
        lines.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{body.symbol_size_px:.2f}" '
            f'fill="{body.color}" stroke="{stroke}" stroke-width="1.5" '
            f'opacity="{opacity:.3f}"/>'
        )
        label_fill = "#fff6d8" if body.kind == "sun" else "#e8eefc"
        lines.append(
            f'<text x="{x + 12.0:.2f}" y="{y - 12.0:.2f}" fill="{label_fill}" '
            'font-size="16" font-family="Menlo, Consolas, monospace">'
            f"{svg_escape(body.name)}"
            "</text>"
        )

    lines.append("</svg>")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def summarize_visible_stars(visible_stars: Sequence[VisibleStar], count: int = 8) -> str:
    preview = visible_stars[:count]
    return "\n".join(
        f"  - {star.name}: alt={star.alt_deg:.2f}°, az={star.az_deg:.2f}°, V={star.vmag:.2f}"
        for star in preview
    )


def summarize_frame_bodies(frame: Dict[str, Any]) -> str:
    labels = []
    for body in frame["moving_bodies"]:
        labels.append(
            f'{body["name"]}: alt={body["alt_deg"]:.2f}°, az={body["az_deg"]:.2f}°, visible={body["visible"]}'
        )
    return " | ".join(labels)
