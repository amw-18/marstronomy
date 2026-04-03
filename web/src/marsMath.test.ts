import { describe, expect, test } from "vitest";

import reference from "./fixtures/mars-reference.json";
import { DEFAULT_SITE, sceneFrameForTime } from "./marsMath";

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
    }
  });
});
