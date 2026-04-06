#!/usr/bin/env python3
"""Generate a Mars sky timeline with stars, the Sun, Phobos, and Deimos."""

from __future__ import annotations

import argparse
import os

try:
    from mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_KEYFRAME_COUNT,
        DEFAULT_SCENE_START_UTC,
        DEFAULT_TIMELINE_DURATION_SOLS,
        DEFAULT_TIMELINE_FRAME_COUNT,
        OLYMPUS_MONS_LAT_DEG,
        OLYMPUS_MONS_LON_EAST_DEG,
        Site,
        approximation_notes,
        build_scene_timeline,
        build_visibility_aware_keyframe_indices,
        build_visible_stars,
        datetime_to_jd_tt,
        default_site,
        load_normalized_catalog,
        parse_iso_utc,
        render_sky_svg,
        scene_bodies_for_time,
        site_payload,
        summarize_frame_bodies,
        utc_isoformat,
        write_json,
    )
except ImportError:
    from scripts.mars_sky_core import (
        CATALOG_DEFAULT,
        DEFAULT_KEYFRAME_COUNT,
        DEFAULT_SCENE_START_UTC,
        DEFAULT_TIMELINE_DURATION_SOLS,
        DEFAULT_TIMELINE_FRAME_COUNT,
        OLYMPUS_MONS_LAT_DEG,
        OLYMPUS_MONS_LON_EAST_DEG,
        Site,
        approximation_notes,
        build_scene_timeline,
        build_visibility_aware_keyframe_indices,
        build_visible_stars,
        datetime_to_jd_tt,
        default_site,
        load_normalized_catalog,
        parse_iso_utc,
        render_sky_svg,
        scene_bodies_for_time,
        site_payload,
        summarize_frame_bodies,
        utc_isoformat,
        write_json,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Mars sky timeline with the Sun, Phobos, and Deimos."
    )
    parser.add_argument(
        "--catalog",
        default=CATALOG_DEFAULT,
        help="Path to the star catalog JSON file.",
    )
    parser.add_argument(
        "--start-utc",
        default=DEFAULT_SCENE_START_UTC,
        help="Timeline start UTC in ISO-8601 form, e.g. 2026-04-06T00:00:00Z.",
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
        "--duration-sols",
        type=float,
        default=DEFAULT_TIMELINE_DURATION_SOLS,
        help="Timeline duration in mean Mars solar days.",
    )
    parser.add_argument(
        "--frame-count",
        type=int,
        default=DEFAULT_TIMELINE_FRAME_COUNT,
        help="Number of timeline frames to emit.",
    )
    parser.add_argument(
        "--keyframe-count",
        type=int,
        default=DEFAULT_KEYFRAME_COUNT,
        help="Number of SVG keyframes to render.",
    )
    parser.add_argument(
        "--mag-limit",
        type=float,
        default=6.5,
        help="Star catalog magnitude cutoff for keyframe rendering.",
    )
    parser.add_argument(
        "--out-timeline-json",
        default="out/olympus_mons_scene_timeline.json",
        help="Path for the timeline JSON output.",
    )
    parser.add_argument(
        "--out-keyframes-dir",
        default="out/olympus_mons_scene_keyframes",
        help="Directory for generated keyframe SVG files.",
    )
    return parser.parse_args()


def build_timeline_payload(
    site: Site,
    start_utc_text: str,
    duration_sols: float,
    frame_count: int,
    frames: list,
    visibility_summary: dict,
    warnings: list,
) -> dict:
    return {
        "site": site_payload(site),
        "timing": {
            "start_utc": start_utc_text,
            "duration_sols": duration_sols,
            "frame_count": frame_count,
        },
        "approximation_notes": approximation_notes(),
        "visibility_summary": visibility_summary,
        "warnings": warnings,
        "frames": frames,
    }


def render_keyframes(
    out_dir: str,
    keyframe_indices: list,
    frames: list,
    site: Site,
    stars: list,
    mag_limit: float,
) -> list:
    os.makedirs(out_dir, exist_ok=True)
    written_paths = []
    for ordinal, frame_index in enumerate(keyframe_indices):
        frame = frames[frame_index]
        dt_utc = parse_iso_utc(frame["utc"])
        jd_tt = datetime_to_jd_tt(dt_utc)
        visible_stars = build_visible_stars(
            stars=stars,
            lat_deg=site.latitude_deg,
            lon_east_deg=site.longitude_east_deg,
            jd_tt=jd_tt,
            mag_limit=mag_limit,
        )
        _, sun, planets, phobos, deimos = scene_bodies_for_time(dt_utc, site)
        out_path = os.path.join(out_dir, f"keyframe_{ordinal:02d}.svg")
        render_sky_svg(
            output_path=out_path,
            visible_stars=visible_stars,
            utc_text=frame["utc"],
            site=site,
            title="Mars Sky Scene POC: Olympus Mons",
            subtitle=(
                f'{frame["utc"]} | star opacity {frame["star_opacity"]:.2f} | '
                f'frame {frame_index + 1}/{len(frames)}'
            ),
            star_opacity=frame["star_opacity"],
            moving_bodies=[sun, *planets.values(), phobos, deimos],
            sun_altitude_deg=sun.alt_deg,
        )
        written_paths.append(out_path)
    return written_paths


def main() -> int:
    args = parse_args()
    start_utc = parse_iso_utc(args.start_utc)
    site = Site(
        name=default_site().name,
        latitude_deg=args.lat,
        longitude_east_deg=args.lon_east,
    )

    stars, sample_keys, record_count = load_normalized_catalog(args.catalog)
    frames = build_scene_timeline(
        start_utc=start_utc,
        site=site,
        duration_sols=args.duration_sols,
        frame_count=args.frame_count,
    )
    keyframe_indices, visibility_summary, warnings = build_visibility_aware_keyframe_indices(
        frames=frames,
        keyframe_count=args.keyframe_count,
    )
    payload = build_timeline_payload(
        site=site,
        start_utc_text=utc_isoformat(start_utc),
        duration_sols=args.duration_sols,
        frame_count=args.frame_count,
        frames=frames,
        visibility_summary=visibility_summary,
        warnings=warnings,
    )
    payload["catalog_schema_hint"] = sample_keys
    payload["catalog_records"] = record_count
    payload["catalog_normalized_stars"] = len(stars)

    write_json(args.out_timeline_json, payload)

    keyframe_paths = render_keyframes(
        out_dir=args.out_keyframes_dir,
        keyframe_indices=keyframe_indices,
        frames=frames,
        site=site,
        stars=stars,
        mag_limit=args.mag_limit,
    )

    print("Catalog schema hint:", ", ".join(sample_keys))
    print(f"Catalog records: {record_count}")
    print(f"Normalized stars: {len(stars)}")
    print(f"Timeline frames: {len(frames)}")
    print(f"Keyframes: {len(keyframe_paths)}")
    print(f"Output JSON: {args.out_timeline_json}")
    print(f"Output keyframes dir: {args.out_keyframes_dir}")
    print(f"Warnings: {len(warnings)}")
    if frames:
        print("First frame bodies:")
        print("  " + summarize_frame_bodies(frames[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
