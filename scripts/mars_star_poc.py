#!/usr/bin/env python3
"""Generate a stars-only Mars sky snapshot from the local bright-star catalog."""

from __future__ import annotations

import argparse

try:
    from mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_UTC,
        OLYMPUS_MONS_LAT_DEG,
        OLYMPUS_MONS_LON_EAST_DEG,
        Site,
        build_visible_stars,
        datetime_to_jd_tt,
        load_normalized_catalog,
        parse_iso_utc,
        render_sky_svg,
        summarize_visible_stars,
        utc_isoformat,
        write_visible_star_snapshot,
    )
except ImportError:
    from scripts.mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_UTC,
        OLYMPUS_MONS_LAT_DEG,
        OLYMPUS_MONS_LON_EAST_DEG,
        Site,
        build_visible_stars,
        datetime_to_jd_tt,
        load_normalized_catalog,
        parse_iso_utc,
        render_sky_svg,
        summarize_visible_stars,
        utc_isoformat,
        write_visible_star_snapshot,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Mars-sky star snapshot from a star catalog."
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


def main() -> int:
    args = parse_args()
    dt_utc = parse_iso_utc(args.utc)
    jd_tt = datetime_to_jd_tt(dt_utc)
    site = Site(
        name="Olympus Mons",
        latitude_deg=args.lat,
        longitude_east_deg=args.lon_east,
    )

    stars, sample_keys, record_count = load_normalized_catalog(args.catalog)
    visible = build_visible_stars(
        stars=stars,
        lat_deg=site.latitude_deg,
        lon_east_deg=site.longitude_east_deg,
        jd_tt=jd_tt,
        mag_limit=args.mag_limit,
    )

    write_visible_star_snapshot(
        output_path=args.out_json,
        visible_stars=visible,
        utc_text=utc_isoformat(dt_utc),
        site=site,
        sample_keys=sample_keys,
    )
    render_sky_svg(
        output_path=args.out_svg,
        visible_stars=visible,
        utc_text=utc_isoformat(dt_utc),
        site=site,
        title="Mars Sky POC: Olympus Mons",
        subtitle=(
            f"{utc_isoformat(dt_utc)} | lat {site.latitude_deg:.2f} | "
            f"lonE {site.longitude_east_deg:.2f}"
        ),
        label_count=args.label_count,
    )

    print("Catalog schema hint:", ", ".join(sample_keys))
    print(f"Catalog records: {record_count}")
    print(f"Normalized stars: {len(stars)}")
    print(f"Visible stars (V <= {args.mag_limit:.1f}): {len(visible)}")
    print(f"Output JSON: {args.out_json}")
    print(f"Output SVG: {args.out_svg}")
    if visible:
        print("Brightest visible stars:")
        print(summarize_visible_stars(visible))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
