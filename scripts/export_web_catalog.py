#!/usr/bin/env python3
"""Export compact runtime data and reference fixtures for the web viewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

try:
    from mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_SCENE_START_UTC,
        default_site,
        ensure_parent_dir,
        kelvin_to_rgb,
        load_normalized_catalog,
        parse_iso_utc,
        scene_bodies_for_time,
        site_payload,
        utc_isoformat,
        vector_from_ra_dec,
    )
except ImportError:
    from scripts.mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_SCENE_START_UTC,
        default_site,
        ensure_parent_dir,
        kelvin_to_rgb,
        load_normalized_catalog,
        parse_iso_utc,
        scene_bodies_for_time,
        site_payload,
        utc_isoformat,
        vector_from_ra_dec,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = ROOT / CATALOG_DEFAULT
DEFAULT_STARS_OUT = ROOT / "web/public/data/stars.min.json"
DEFAULT_FIXTURE_OUT = ROOT / "web/src/fixtures/mars-reference.json"
REFERENCE_TIMESTAMPS: Sequence[str] = (
    "2026-01-15T18:00:00Z",
    DEFAULT_SCENE_START_UTC,
    "2026-04-06T12:00:00Z",
    "2026-07-15T00:00:00Z",
    "2026-04-07T06:00:00Z",
    "2026-10-07T06:00:00Z",
)


def compact_json_dump(path: Path | str, payload: Any) -> None:
    target_path = Path(path)
    ensure_parent_dir(str(target_path))
    with open(target_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=True)


def export_stars(catalog_path: Path | str) -> Dict[str, Any]:
    stars, sample_keys, record_count = load_normalized_catalog(str(catalog_path))
    compact = [
        {
            "h": star.hr,
            "n": star.name,
            "m": round(star.vmag, 3),
            "rgb": kelvin_to_rgb(star.kelvin),
            "eci": [round(component, 8) for component in vector_from_ra_dec(star.ra_deg, star.dec_deg)],
        }
        for star in sorted(stars, key=lambda value: (value.vmag, value.name))
    ]
    return {
        "record_count": record_count,
        "normalized_count": len(stars),
        "sample_keys": sample_keys,
        "stars": compact,
    }


def body_payload(body: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "alt_deg": round(body.alt_deg, 6),
        "az_deg": round(body.az_deg, 6),
        "visible": body.visible,
    }
    if body.distance_km is not None:
        payload["distance_km"] = round(body.distance_km, 6)
    if body.distance_au is not None:
        payload["distance_au"] = round(body.distance_au, 6)
    if body.phase_angle_deg is not None:
        payload["phase_angle_deg"] = round(body.phase_angle_deg, 6)
    if body.illuminated_fraction is not None:
        payload["illuminated_fraction"] = round(body.illuminated_fraction, 6)
    if body.terminator_angle_deg is not None:
        payload["terminator_angle_deg"] = round(body.terminator_angle_deg, 6)
    if body.apparent_diameter_arcmin is not None:
        payload["apparent_diameter_arcmin"] = round(body.apparent_diameter_arcmin, 6)
    if body.resolved_in_main_view is not None:
        payload["resolved_in_main_view"] = body.resolved_in_main_view
    if body.apparent_magnitude is not None:
        payload["apparent_magnitude"] = round(body.apparent_magnitude, 6)
    return payload


def export_reference_fixtures() -> Dict[str, Any]:
    site = default_site()
    cases: List[Dict[str, Any]] = []

    for utc_text in REFERENCE_TIMESTAMPS:
        dt_utc = parse_iso_utc(utc_text)
        solar, sun, planets, phobos, deimos = scene_bodies_for_time(dt_utc, site)
        cases.append(
            {
                "utc": utc_isoformat(dt_utc),
                "ltst_hours": round(solar.ltst_hours, 6),
                "sun": body_payload(sun),
                "planets": {
                    kind: body_payload(body)
                    for kind, body in planets.items()
                },
                "phobos": body_payload(phobos),
                "deimos": body_payload(deimos),
            }
        )

    return {
        "site": site_payload(site),
        "cases": cases,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the compact star catalog and browser reference fixtures."
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG_PATH),
        help="Path to the source star catalog JSON file.",
    )
    parser.add_argument(
        "--stars-out",
        default=str(DEFAULT_STARS_OUT),
        help="Path for the compact runtime star catalog JSON.",
    )
    parser.add_argument(
        "--fixture-out",
        default=str(DEFAULT_FIXTURE_OUT),
        help="Path for the browser reference fixture JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exported = export_stars(args.catalog)
    compact_json_dump(args.stars_out, exported["stars"])
    compact_json_dump(args.fixture_out, export_reference_fixtures())

    print(f"Catalog records: {exported['record_count']}")
    print(f"Normalized stars: {exported['normalized_count']}")
    print(f"Catalog schema hint: {', '.join(exported['sample_keys'])}")
    print(f"Runtime star output: {args.stars_out}")
    print(f"Reference fixtures: {args.fixture_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
