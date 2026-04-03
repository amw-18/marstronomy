from __future__ import annotations

import pathlib
import sys
import unittest
from datetime import timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mars_sky_core import (
    DEFAULT_KEYFRAME_COUNT,
    DEFAULT_TIMELINE_DURATION_SOLS,
    DEFAULT_TIMELINE_FRAME_COUNT,
    DEFAULT_UTC,
    DEIMOS_MODEL,
    PHOBOS_MODEL,
    build_keyframe_indices,
    build_moon_body,
    build_scene_timeline,
    build_sun_body,
    datetime_to_jd_tt,
    default_site,
    direction_to_alt_az,
    mars_solar_data,
    moon_body_position,
    moon_opacity_from_sun_altitude,
    parse_iso_utc,
    star_opacity_from_sun_altitude,
)


class MarsSkyCoreTests(unittest.TestCase):
    def test_mars24_worked_example_matches_reference(self) -> None:
        dt_utc = parse_iso_utc("2000-01-06T00:00:00Z")
        jd_tt = datetime_to_jd_tt(dt_utc)
        solar = mars_solar_data(jd_tt, longitude_east_deg=0.0)
        sun = build_sun_body(solar, lat_deg=0.0, lon_east_deg=0.0)

        self.assertAlmostEqual(solar.mst_hours, 23.99425, delta=0.0002)
        self.assertAlmostEqual(solar.eot_deg, -5.18774, delta=0.02)
        self.assertAlmostEqual(solar.subsolar_longitude_west_deg, 174.72600, delta=0.03)
        self.assertAlmostEqual(solar.solar_declination_deg, -25.22825, delta=0.03)
        self.assertAlmostEqual(sun.alt_deg, -64.26182, delta=0.12)
        self.assertAlmostEqual(sun.az_deg, 191.03905, delta=0.25)

    def test_daylight_visibility_curve_keeps_stars_dimmed_not_gone(self) -> None:
        self.assertAlmostEqual(star_opacity_from_sun_altitude(-30.0), 1.0, delta=1e-9)
        self.assertLess(star_opacity_from_sun_altitude(20.0), 0.09)
        self.assertGreater(star_opacity_from_sun_altitude(20.0), 0.0)
        self.assertGreater(
            moon_opacity_from_sun_altitude(20.0),
            star_opacity_from_sun_altitude(20.0),
        )

    def test_phobos_and_deimos_rise_on_expected_horizon_sides(self) -> None:
        site = default_site()
        start = parse_iso_utc(DEFAULT_UTC)

        def first_rising_azimuth(model) -> float:
            prev_alt = None
            for step_index in range(0, 7 * 24 * 6):
                dt_utc = start + timedelta(minutes=10 * step_index)
                jd_tt = datetime_to_jd_tt(dt_utc)
                body = build_moon_body(
                    model,
                    jd_tt,
                    site.latitude_deg,
                    site.longitude_east_deg,
                    observer_radius_km=site.radius_km,
                )
                if prev_alt is not None and prev_alt <= 0.0 < body.alt_deg:
                    return body.az_deg
                prev_alt = body.alt_deg
            self.fail(f"Could not find a rising event for {model.name}.")

        phobos_rise_az = first_rising_azimuth(PHOBOS_MODEL)
        deimos_rise_az = first_rising_azimuth(DEIMOS_MODEL)

        self.assertGreater(phobos_rise_az, 180.0)
        self.assertLess(phobos_rise_az, 360.0)
        self.assertGreaterEqual(deimos_rise_az, 0.0)
        self.assertLess(deimos_rise_az, 180.0)

    def test_phobos_uses_topocentric_parallax(self) -> None:
        site = default_site()
        start = parse_iso_utc(DEFAULT_UTC)

        for step_index in range(0, 24 * 12):
            dt_utc = start + timedelta(minutes=5 * step_index)
            jd_tt = datetime_to_jd_tt(dt_utc)
            body = build_moon_body(
                PHOBOS_MODEL,
                jd_tt,
                site.latitude_deg,
                site.longitude_east_deg,
                observer_radius_km=site.radius_km,
            )
            if body.alt_deg > 10.0:
                position_body, _ = moon_body_position(PHOBOS_MODEL, jd_tt)
                geocentric_alt_deg, _ = direction_to_alt_az(
                    position_body,
                    site.latitude_deg,
                    site.longitude_east_deg,
                )
                self.assertGreater(abs(body.alt_deg - geocentric_alt_deg), 1.0)
                return
        self.fail("Could not find a visible Phobos sample for the parallax test.")

    def test_timeline_defaults_match_contract(self) -> None:
        start_utc = parse_iso_utc(DEFAULT_UTC)
        site = default_site()
        frames = build_scene_timeline(
            start_utc=start_utc,
            site=site,
            duration_sols=DEFAULT_TIMELINE_DURATION_SOLS,
            frame_count=DEFAULT_TIMELINE_FRAME_COUNT,
        )
        keyframe_indices = build_keyframe_indices(
            frame_count=len(frames),
            keyframe_count=DEFAULT_KEYFRAME_COUNT,
        )

        self.assertEqual(len(frames), DEFAULT_TIMELINE_FRAME_COUNT)
        self.assertEqual(len(keyframe_indices), DEFAULT_KEYFRAME_COUNT)
        self.assertEqual(keyframe_indices[0], 0)
        self.assertEqual(keyframe_indices[-1], len(frames) - 1)
        self.assertIn("sun_alt_deg", frames[0])
        self.assertIn("star_opacity", frames[0])
        self.assertEqual(
            {body["kind"] for body in frames[0]["moving_bodies"]},
            {"sun", "phobos", "deimos"},
        )


if __name__ == "__main__":
    unittest.main()
