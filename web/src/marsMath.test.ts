import { describe, expect, test } from "vitest";

import { PLANET_KINDS } from "./constants";
import reference from "./fixtures/mars-reference.json";
import {
  DEFAULT_SITE,
  bodyToInertial,
  dot,
  marsBodyBasis,
  marsCelestialBasis,
  marsOrientation,
  sceneFrameForTime,
  sunDirectionBody,
  vectorFromCelestialBasis,
} from "./marsMath";

function expectNear(actual: number, expected: number, tolerance = 1e-4): void {
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(tolerance);
}

describe("mars browser math", () => {
  test("matches the Python reference fixtures for the Sun and both moons", () => {
    for (const fixtureCase of reference.cases) {
      const frame = sceneFrameForTime(Date.parse(fixtureCase.utc), DEFAULT_SITE);

      expectNear(frame.solarData.ltstHours, fixtureCase.ltst_hours, 1e-4);
      expectNear(frame.bodies.sun.altDeg, fixtureCase.sun.alt_deg, 1e-4);
      expectNear(frame.bodies.sun.azDeg, fixtureCase.sun.az_deg, 1e-4);

      expectNear(frame.bodies.phobos.altDeg, fixtureCase.phobos.alt_deg, 1e-4);
      expectNear(frame.bodies.phobos.azDeg, fixtureCase.phobos.az_deg, 1e-4);
      expectNear(
        frame.bodies.phobos.illuminatedFraction ?? 0,
        fixtureCase.phobos.illuminated_fraction,
        1e-4,
      );

      expectNear(frame.bodies.deimos.altDeg, fixtureCase.deimos.alt_deg, 1e-4);
      expectNear(frame.bodies.deimos.azDeg, fixtureCase.deimos.az_deg, 1e-4);
      expectNear(
        frame.bodies.deimos.illuminatedFraction ?? 0,
        fixtureCase.deimos.illuminated_fraction,
        1e-4,
      );

      for (const kind of PLANET_KINDS) {
        expectNear(frame.planets[kind].altDeg, fixtureCase.planets[kind].alt_deg, 1e-4);
        expectNear(frame.planets[kind].azDeg, fixtureCase.planets[kind].az_deg, 1e-4);
        expectNear(
          frame.planets[kind].illuminatedFraction ?? 0,
          fixtureCase.planets[kind].illuminated_fraction,
          1e-4,
        );
        expectNear(
          frame.planets[kind].apparentMagnitude ?? 0,
          fixtureCase.planets[kind].apparent_magnitude,
          1e-4,
        );
      }
    }
  });

  test("builds a Mars celestial basis aligned with the equator and ecliptic", () => {
    const frame = sceneFrameForTime(Date.parse("2026-04-06T00:00:00Z"), DEFAULT_SITE);
    const basis = marsCelestialBasis(frame.solarData.jdTt);
    const obliquityDeg = (Math.acos(dot(basis.pole, basis.orbitPole)) * 180) / Math.PI;
    expectNear(obliquityDeg, 25.19, 0.2);
    expect(Math.abs(dot(basis.equinox, basis.pole))).toBeLessThan(1e-6);
    expect(Math.abs(dot(basis.equinox, basis.orbitPole))).toBeLessThan(1e-6);

    const justPastEquinox = vectorFromCelestialBasis(
      1,
      0,
      basis.equinox,
      basis.eclipticEast,
      basis.orbitPole,
    );
    const declinationDeg = (Math.asin(dot(justPastEquinox, basis.pole)) * 180) / Math.PI;
    expect(declinationDeg).toBeGreaterThan(0);

    const [poleRaDeg, poleDecDeg, primeMeridianDeg] = marsOrientation(frame.solarData.jdTt);
    const [xBody, yBody, zBody] = marsBodyBasis(poleRaDeg, poleDecDeg, primeMeridianDeg);
    const sunInertial = bodyToInertial(sunDirectionBody(frame.solarData), xBody, yBody, zBody);
    expectNear(dot(sunInertial, basis.orbitPole), 0, 5e-3);
  });

  test("scopes the implemented planets to the naked-eye set", () => {
    const frame = sceneFrameForTime(Date.parse("2026-04-06T00:00:00Z"), DEFAULT_SITE);
    expect(Object.keys(frame.planets).sort()).toEqual(["earth", "jupiter", "mercury", "saturn", "venus"]);
    expect("uranus" in frame.planets).toBe(false);
    expect("neptune" in frame.planets).toBe(false);
  });
});
