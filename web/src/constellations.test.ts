import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, test } from "vitest";

import { resolveConstellations } from "./constellations";
import { CONSTELLATION_DEFINITIONS } from "./constellationData";
import type { RuntimeStar } from "./types";

const stars = JSON.parse(
  readFileSync(path.resolve(process.cwd(), "public/data/stars.min.json"), "utf8"),
) as RuntimeStar[];

describe("constellation overlay data", () => {
  test("contains all 88 constellations with valid HR references", () => {
    const starHrs = new Set(stars.map((star) => star.h));
    expect(CONSTELLATION_DEFINITIONS).toHaveLength(88);
    expect(new Set(CONSTELLATION_DEFINITIONS.map((definition) => definition.abbr)).size).toBe(88);
    expect(new Set(CONSTELLATION_DEFINITIONS.map((definition) => definition.name)).size).toBe(88);

    for (const definition of CONSTELLATION_DEFINITIONS) {
      expect(definition.segments.length).toBeGreaterThan(0);
      expect(starHrs.has(definition.labelHr)).toBe(true);
      for (const [startHr, endHr] of definition.segments) {
        expect(starHrs.has(startHr)).toBe(true);
        expect(starHrs.has(endHr)).toBe(true);
      }
    }
  });

  test("resolves runtime vectors for every constellation", () => {
    const resolved = resolveConstellations(stars);
    expect(resolved).toHaveLength(88);
    expect(resolved.every((constellation) => constellation.segments.length > 0)).toBe(true);
  });
});
