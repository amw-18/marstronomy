from __future__ import annotations

import pathlib
import sys
import unittest
import math
from datetime import timedelta


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mars_sky_core import (
    DEFAULT_KEYFRAME_COUNT,
    DEFAULT_SCENE_START_UTC,
    DEFAULT_TIMELINE_DURATION_SOLS,
    DEFAULT_TIMELINE_FRAME_COUNT,
    DEFAULT_UTC,
    DEIMOS_MODEL,
    PLANET_MODELS,
    PHOBOS_MODEL,
    build_keyframe_indices,
    build_moon_body,
    build_planet_body,
    build_scene_timeline,
    build_sun_body,
    build_visibility_aware_keyframe_indices,
    datetime_to_jd_tt,
    default_site,
    direction_to_alt_az,
    mars_solar_data,
    moon_body_position,
    moon_opacity_from_sun_altitude,
    parse_iso_utc,
    phase_geometry_from_local_vectors,
    star_opacity_from_sun_altitude,
)


class MarsSkyCoreTests(unittest.TestCase):
    def test_scoped_planets_are_exported_in_scene_frames(self) -> None:
        site = default_site()
        frames = build_scene_timeline(
            start_utc=parse_iso_utc(DEFAULT_SCENE_START_UTC),
            site=site,
            duration_sols=DEFAULT_TIMELINE_DURATION_SOLS,
            frame_count=DEFAULT_TIMELINE_FRAME_COUNT,
        )
        frame = frames[0]

        self.assertEqual(
            set(frame["planets"].keys()),
            {"mercury", "venus", "earth", "jupiter", "saturn"},
        )
        self.assertNotIn("uranus", frame["planets"])
        self.assertNotIn("neptune", frame["planets"])
        self.assertEqual(
            {body["kind"] for body in frame["moving_bodies"]},
            {"sun", "mercury", "venus", "earth", "jupiter", "saturn", "phobos", "deimos"},
        )

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

    def test_phase_geometry_handles_full_half_and_crescent_cases(self) -> None:
        full = phase_geometry_from_local_vectors(
            observer_from_moon_local=(0.0, 0.0, 1.0),
            sun_from_moon_local=(0.0, 0.0, 1.0),
            apparent_diameter_arcmin=10.0,
            symbol_size_px=8.5,
        )
        half = phase_geometry_from_local_vectors(
            observer_from_moon_local=(0.0, 0.0, 1.0),
            sun_from_moon_local=(1.0, 0.0, 0.0),
            apparent_diameter_arcmin=10.0,
            symbol_size_px=8.5,
        )
        crescent = phase_geometry_from_local_vectors(
            observer_from_moon_local=(0.0, 0.0, 1.0),
            sun_from_moon_local=(0.8660254, 0.0, -0.5),
            apparent_diameter_arcmin=10.0,
            symbol_size_px=8.5,
        )
        opposite_half = phase_geometry_from_local_vectors(
            observer_from_moon_local=(0.0, 0.0, 1.0),
            sun_from_moon_local=(-1.0, 0.0, 0.0),
            apparent_diameter_arcmin=10.0,
            symbol_size_px=8.5,
        )

        self.assertAlmostEqual(full.illuminated_fraction, 1.0, delta=1e-6)
        self.assertAlmostEqual(half.illuminated_fraction, 0.5, delta=1e-6)
        self.assertAlmostEqual(crescent.illuminated_fraction, 0.25, delta=1e-4)
        self.assertAlmostEqual(half.phase_angle_deg, 90.0, delta=1e-6)
        self.assertAlmostEqual(crescent.phase_angle_deg, 120.0, delta=1e-3)
        self.assertAlmostEqual(
            abs(half.terminator_angle_deg - opposite_half.terminator_angle_deg),
            180.0,
            delta=1e-6,
        )
        for geometry in (full, half, crescent, opposite_half):
            self.assertGreaterEqual(geometry.illuminated_fraction, 0.0)
            self.assertLessEqual(geometry.illuminated_fraction, 1.0)

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
                    sun_direction_body=(1.0, 0.0, 0.0),
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
                sun_direction_body=(1.0, 0.0, 0.0),
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
        start_utc = parse_iso_utc(DEFAULT_SCENE_START_UTC)
        site = default_site()
        frames = build_scene_timeline(
            start_utc=start_utc,
            site=site,
            duration_sols=DEFAULT_TIMELINE_DURATION_SOLS,
            frame_count=DEFAULT_TIMELINE_FRAME_COUNT,
        )
        keyframe_indices, visibility_summary, warnings = build_visibility_aware_keyframe_indices(
            frames=frames,
            keyframe_count=DEFAULT_KEYFRAME_COUNT,
        )

        self.assertEqual(len(frames), DEFAULT_TIMELINE_FRAME_COUNT)
        self.assertEqual(len(keyframe_indices), DEFAULT_KEYFRAME_COUNT)
        self.assertEqual(keyframe_indices[0], 0)
        self.assertEqual(keyframe_indices[-1], len(frames) - 1)
        self.assertIn("sun_alt_deg", frames[0])
        self.assertIn("star_opacity", frames[0])
        self.assertEqual(
            set(frames[0]["planets"].keys()),
            set(PLANET_MODELS.keys()),
        )
        self.assertEqual(
            {body["kind"] for body in frames[0]["moving_bodies"]},
            {"sun", "mercury", "venus", "earth", "jupiter", "saturn", "phobos", "deimos"},
        )
        self.assertGreater(visibility_summary["deimos"]["visible_frame_count"], 0)
        self.assertGreater(visibility_summary["deimos"]["keyframe_visible_count"], 0)
        self.assertEqual(warnings, [])

    def test_planet_bodies_have_reasonable_geometry(self) -> None:
        site = default_site()
        jd_tt = datetime_to_jd_tt(parse_iso_utc(DEFAULT_SCENE_START_UTC))
        previous_jupiter = build_planet_body(PLANET_MODELS["jupiter"], jd_tt, site)

        for kind, model in PLANET_MODELS.items():
            body = build_planet_body(model, jd_tt, site)
            self.assertGreaterEqual(body.illuminated_fraction or 0.0, 0.0)
            self.assertLessEqual(body.illuminated_fraction or 0.0, 1.0)
            self.assertIsNotNone(body.distance_au)
            self.assertGreater(body.distance_au or 0.0, 0.0)
            self.assertIsNotNone(body.apparent_magnitude)

        later = build_planet_body(
            PLANET_MODELS["jupiter"],
            jd_tt + 7.0,
            site,
        )
        self.assertLess(
            abs((later.apparent_magnitude or 0.0) - (previous_jupiter.apparent_magnitude or 0.0)),
            0.5,
        )

    def test_mercury_can_be_visible_while_staying_close_to_the_sun(self) -> None:
        def angular_separation_deg(a_alt: float, a_az: float, b_alt: float, b_az: float) -> float:
            a_alt_rad = math.radians(a_alt)
            b_alt_rad = math.radians(b_alt)
            delta_az_rad = math.radians(a_az - b_az)
            cosine = (
                (math.sin(a_alt_rad) * math.sin(b_alt_rad))
                + (math.cos(a_alt_rad) * math.cos(b_alt_rad) * math.cos(delta_az_rad))
            )
            return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))

        site = default_site()
        start = parse_iso_utc("2026-01-01T00:00:00Z")
        for step_index in range(0, 365 * 6):
            dt_utc = start + timedelta(hours=4 * step_index)
            jd_tt = datetime_to_jd_tt(dt_utc)
            solar = mars_solar_data(jd_tt, site.longitude_east_deg)
            sun = build_sun_body(solar, site.latitude_deg, site.longitude_east_deg)
            mercury = build_planet_body(PLANET_MODELS["mercury"], jd_tt, site)
            separation_deg = angular_separation_deg(
                mercury.alt_deg,
                mercury.az_deg,
                sun.alt_deg,
                sun.az_deg,
            )
            if mercury.visible and separation_deg < 28.0:
                self.assertIsNotNone(mercury.apparent_magnitude)
                self.assertLess(separation_deg, 28.0)
                return
        self.fail("Could not find a Mercury sample that is visible yet still close to the Sun.")

    def test_default_scene_resolves_phobos_but_not_deimos_in_main_view(self) -> None:
        site = default_site()
        frames = build_scene_timeline(
            start_utc=parse_iso_utc(DEFAULT_SCENE_START_UTC),
            site=site,
            duration_sols=DEFAULT_TIMELINE_DURATION_SOLS,
            frame_count=DEFAULT_TIMELINE_FRAME_COUNT,
        )
        phobos_resolved = any(
            next(body for body in frame["moving_bodies"] if body["kind"] == "phobos")[
                "resolved_in_main_view"
            ]
            for frame in frames
        )
        deimos_resolved = any(
            next(body for body in frame["moving_bodies"] if body["kind"] == "deimos")[
                "resolved_in_main_view"
            ]
            for frame in frames
        )

        self.assertTrue(phobos_resolved)
        self.assertFalse(deimos_resolved)

    def test_no_deimos_window_emits_visibility_warning(self) -> None:
        site = default_site()
        frames = build_scene_timeline(
            start_utc=parse_iso_utc(DEFAULT_UTC),
            site=site,
            duration_sols=DEFAULT_TIMELINE_DURATION_SOLS,
            frame_count=DEFAULT_TIMELINE_FRAME_COUNT,
        )
        keyframe_indices, visibility_summary, warnings = build_visibility_aware_keyframe_indices(
            frames=frames,
            keyframe_count=DEFAULT_KEYFRAME_COUNT,
        )

        self.assertEqual(visibility_summary["deimos"]["visible_frame_count"], 0)
        self.assertEqual(visibility_summary["deimos"]["keyframe_visible_count"], 0)
        self.assertTrue(
            any("Deimos" in warning and "below the horizon" in warning for warning in warnings)
        )
        self.assertEqual(len(keyframe_indices), DEFAULT_KEYFRAME_COUNT)


if __name__ == "__main__":
    unittest.main()
