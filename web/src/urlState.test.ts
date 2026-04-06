import { describe, expect, test } from "vitest";

import { DEFAULT_VIEWER_STATE } from "./constants";
import { readStateFromSearch, writeStateToSearch } from "./urlState";

describe("viewer url state", () => {
  test("round-trips grid and ecliptic settings", () => {
    const state = {
      ...DEFAULT_VIEWER_STATE(),
      simUtcMs: Date.parse("2026-04-06T03:21:45Z"),
      speedSecondsPerSecond: 300,
      yawDeg: 212.5,
      pitchDeg: 18.25,
      fovDeg: 68.5,
      showAzimuthalGrid: true,
      showEquatorialGrid: true,
      showEcliptic: false,
    };

    const roundTripped = readStateFromSearch(writeStateToSearch(state));
    expect(roundTripped.simUtcMs).toBe(state.simUtcMs);
    expect(roundTripped.speedSecondsPerSecond).toBe(state.speedSecondsPerSecond);
    expect(roundTripped.yawDeg).toBeCloseTo(state.yawDeg, 2);
    expect(roundTripped.pitchDeg).toBeCloseTo(state.pitchDeg, 2);
    expect(roundTripped.fovDeg).toBeCloseTo(state.fovDeg, 2);
    expect(roundTripped.showAzimuthalGrid).toBe(true);
    expect(roundTripped.showEquatorialGrid).toBe(true);
    expect(roundTripped.showEcliptic).toBe(false);
  });

  test("maps legacy shared grid mode urls onto the new toggles", () => {
    const parsed = readStateFromSearch("?grid=equatorial&ecliptic=1");
    expect(parsed.showAzimuthalGrid).toBe(false);
    expect(parsed.showEquatorialGrid).toBe(true);
    expect(parsed.showEcliptic).toBe(true);
  });
});
