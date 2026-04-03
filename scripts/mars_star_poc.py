#!/usr/bin/env python3
"""Generate a Mars-sky proof of concept from a Bright Star Catalog JSON file.

This script intentionally avoids astronomy dependencies so it can run in a bare
Python environment. It:

1. Loads a local BSC/Hipparcos-style JSON catalog.
2. Infers a usable schema without hard-coding a single file variant.
3. Computes Mars body orientation from the IAU/NAIF rotation model.
4. Converts catalog RA/Dec into altitude/azimuth for an Olympus Mons observer.
5. Writes a normalized visible-star snapshot and a simple SVG sky plot.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


CATALOG_DEFAULT = "bsc5.json"
DEFAULT_UTC = "2026-04-04T00:00:00Z"
OLYMPUS_MONS_LAT_DEG = 18.65
OLYMPUS_MONS_LON_EAST_DEG = 226.2

# For dates after 2017-01-01 UTC, TT-UTC = 69.184 s.
# NASA Mars24 notes that no leap seconds had been added beyond 2016 as of
# its 2025-01-07 update, which covers the 2026 default used by this POC.
TT_MINUS_UTC_SECONDS_DEFAULT = 69.184

# IAU/NAIF Mars rotation constants.
MARS_POLE_RA_0_DEG = 317.68143
MARS_POLE_RA_RATE_DEG_PER_CENTURY = -0.1061
MARS_POLE_DEC_0_DEG = 52.88650
MARS_POLE_DEC_RATE_DEG_PER_CENTURY = -0.0609
MARS_PM_0_DEG = 176.630
MARS_PM_RATE_DEG_PER_DAY = 350.89198226
JD_J2000 = 2451545.0
JULIAN_CENTURY_DAYS = 36525.0


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


@dataclass
class Star:
    hr: Optional[int]
    name: str
    ra_deg: float
    dec_deg: float
    vmag: float
    kelvin: Optional[float]


@dataclass
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Mars-sky proof of concept from a star catalog."
    )
    parser.add_argument(
        "--catalog",
        default=CATALOG_DEFAULT,
        help="Path to the star catalog JSON file.",
    )
    parser.add_argument(
        "--utc",
        default=DEFAULT_UTC,
        help="UTC timestamp in ISO-8601 form, e.g. 2026-04-04T00:00:00Z.",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=OLYMPUS_MONS_LAT_DEG,
        help="Observer latitude in planetocentric degrees north.",
    )
    parser.add_argument(
        "--lon-east",
        type=float,
        default=OLYMPUS_MONS_LON_EAST_DEG,
        help="Observer longitude in degrees east.",
    )
    parser.add_argument(
        "--mag-limit",
        type=float,
        default=6.5,
        help="Only include stars brighter than or equal to this visual magnitude.",
    )
    parser.add_argument(
        "--label-count",
        type=int,
        default=18,
        help="Number of brightest stars to label in the SVG plot.",
    )
    parser.add_argument(
        "--out-json",
        default="out/olympus_mons_visible_stars.json",
        help="Path for the normalized visible-star JSON output.",
    )
    parser.add_argument(
        "--out-svg",
        default="out/olympus_mons_sky.svg",
        help="Path for the SVG sky plot output.",
    )
    return parser.parse_args()


def parse_iso_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def datetime_to_jd_utc(dt: datetime) -> float:
    unix_seconds = dt.timestamp()
    return 2440587.5 + (unix_seconds / 86400.0)


def tt_minus_utc_seconds(dt_utc: datetime) -> float:
    fallback = TT_MINUS_UTC_SECONDS_DEFAULT
    for threshold_str, value in reversed(LEAP_SECOND_TABLE):
        if dt_utc >= parse_iso_utc(threshold_str):
            return value
    return fallback


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


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


def deg_to_rad(value: float) -> float:
    return math.radians(value)


def wrap_degrees(value: float) -> float:
    return value % 360.0


def wrap_hours(value: float) -> float:
    return value % 24.0


def mars_orientation(jd_tt: float) -> Tuple[float, float, float]:
    d = jd_tt - JD_J2000
    t = d / JULIAN_CENTURY_DAYS
    pole_ra_deg = MARS_POLE_RA_0_DEG + (MARS_POLE_RA_RATE_DEG_PER_CENTURY * t)
    pole_dec_deg = MARS_POLE_DEC_0_DEG + (MARS_POLE_DEC_RATE_DEG_PER_CENTURY * t)
    prime_meridian_deg = wrap_degrees(MARS_PM_0_DEG + (MARS_PM_RATE_DEG_PER_DAY * d))
    return pole_ra_deg, pole_dec_deg, prime_meridian_deg


def vector_from_ra_dec(ra_deg: float, dec_deg: float) -> Tuple[float, float, float]:
    ra = deg_to_rad(ra_deg)
    dec = deg_to_rad(dec_deg)
    cos_dec = math.cos(dec)
    return (
        cos_dec * math.cos(ra),
        cos_dec * math.sin(ra),
        math.sin(dec),
    )


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    )


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


def local_basis(lat_deg: float, lon_east_deg: float) -> Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]:
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
    body_vector: Sequence[float],
    east: Sequence[float],
    north: Sequence[float],
    up: Sequence[float],
) -> Tuple[float, float]:
    e_comp = dot(body_vector, east)
    n_comp = dot(body_vector, north)
    u_comp = dot(body_vector, up)
    u_comp = max(-1.0, min(1.0, u_comp))
    alt_deg = math.degrees(math.asin(u_comp))
    az_deg = wrap_degrees(math.degrees(math.atan2(e_comp, n_comp)))
    return alt_deg, az_deg


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
        blue = 0.0 if temp <= 19.0 else 138.5177312231 * math.log(temp - 10.0) - 305.0447927307
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


def write_visible_json(
    output_path: str,
    visible_stars: Sequence[VisibleStar],
    utc_text: str,
    lat_deg: float,
    lon_east_deg: float,
    sample_keys: Sequence[str],
) -> None:
    ensure_parent_dir(output_path)
    payload = {
        "site": {
            "name": "Olympus Mons",
            "latitude_deg": lat_deg,
            "longitude_east_deg": lon_east_deg,
            "longitude_west_deg": wrap_degrees(360.0 - lon_east_deg),
        },
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
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(
    output_path: str,
    visible_stars: Sequence[VisibleStar],
    utc_text: str,
    lat_deg: float,
    lon_east_deg: float,
    label_count: int,
) -> None:
    ensure_parent_dir(output_path)

    width = 1200
    height = 1200
    cx = width / 2.0
    cy = height / 2.0
    radius = 500.0

    rings = [15, 30, 45, 60, 75]
    cardinals = [("N", 0.0), ("E", 90.0), ("S", 180.0), ("W", 270.0)]

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
            "Mars Sky POC: Olympus Mons"
            "</text>"
        ),
        (
            f'<text x="{cx}" y="106" fill="#a9b7d9" font-size="18" '
            'font-family="Menlo, Consolas, monospace" text-anchor="middle">'
            f"{svg_escape(utc_text)} UTC | lat {lat_deg:.2f} | lonE {lon_east_deg:.2f}"
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
        if star.name == "Unnamed":
            continue
        labeled.add((star.hr, star.name))

    for star in visible_stars:
        r = radius * ((90.0 - star.alt_deg) / 90.0)
        az = deg_to_rad(star.az_deg)
        x = cx + r * math.sin(az)
        y = cy - r * math.cos(az)
        opacity = min(1.0, max(0.35, 1.1 - (star.vmag / 9.0)))
        lines.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{star.size_px:.2f}" '
            f'fill="{star.rgb}" opacity="{opacity:.3f}" filter="url(#glow)"/>'
        )
        if (star.hr, star.name) in labeled:
            label_x = x + 10.0
            label_y = y - 10.0
            lines.append(
                f'<text x="{label_x:.2f}" y="{label_y:.2f}" fill="#c9d7f4" '
                'font-size="15" font-family="Menlo, Consolas, monospace">'
                f"{svg_escape(star.name)}"
                "</text>"
            )

    lines.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def summarize_visible_stars(visible_stars: Sequence[VisibleStar]) -> str:
    preview = visible_stars[:8]
    lines = []
    for star in preview:
        lines.append(
            f"  - {star.name}: alt={star.alt_deg:.2f}°, az={star.az_deg:.2f}°, V={star.vmag:.2f}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    dt_utc = parse_iso_utc(args.utc)
    jd_utc = datetime_to_jd_utc(dt_utc)
    jd_tt = jd_utc + (tt_minus_utc_seconds(dt_utc) / 86400.0)

    records, sample_keys = load_catalog(args.catalog)
    normalized = [star for star in (normalize_star(record) for record in records) if star]
    visible = build_visible_stars(
        stars=normalized,
        lat_deg=args.lat,
        lon_east_deg=args.lon_east,
        jd_tt=jd_tt,
        mag_limit=args.mag_limit,
    )

    write_visible_json(
        output_path=args.out_json,
        visible_stars=visible,
        utc_text=dt_utc.isoformat().replace("+00:00", "Z"),
        lat_deg=args.lat,
        lon_east_deg=args.lon_east,
        sample_keys=sample_keys,
    )
    render_svg(
        output_path=args.out_svg,
        visible_stars=visible,
        utc_text=dt_utc.isoformat().replace("+00:00", "Z"),
        lat_deg=args.lat,
        lon_east_deg=args.lon_east,
        label_count=args.label_count,
    )

    print("Catalog schema hint:", ", ".join(sample_keys))
    print(f"Catalog records: {len(records)}")
    print(f"Normalized stars: {len(normalized)}")
    print(f"Visible stars (V <= {args.mag_limit:.1f}): {len(visible)}")
    print(f"Output JSON: {args.out_json}")
    print(f"Output SVG: {args.out_svg}")
    if visible:
        print("Brightest visible stars:")
        print(summarize_visible_stars(visible))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
