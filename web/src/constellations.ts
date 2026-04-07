import { CONSTELLATION_DEFINITIONS } from "./constellationData";
import { normalizeVector } from "./marsMath";
import type { RuntimeConstellation, RuntimeStar, Vec3 } from "./types";

function sumVectors(vectors: Vec3[]): Vec3 {
  return vectors.reduce<Vec3>(
    (sum, vector) => [sum[0] + vector[0], sum[1] + vector[1], sum[2] + vector[2]],
    [0, 0, 0],
  );
}

export function resolveConstellations(stars: RuntimeStar[]): RuntimeConstellation[] {
  const starsByHr = new Map<number, RuntimeStar>();
  for (const star of stars) {
    if (star.h !== null) {
      starsByHr.set(star.h, star);
    }
  }

  return CONSTELLATION_DEFINITIONS.map((definition) => {
    const labelStar = starsByHr.get(definition.labelHr);
    if (!labelStar) {
      throw new Error(`Missing constellation label star HR ${definition.labelHr} for ${definition.name}.`);
    }

    const segments = definition.segments.map(([startHr, endHr]) => {
      const startStar = starsByHr.get(startHr);
      const endStar = starsByHr.get(endHr);
      if (!startStar || !endStar) {
        throw new Error(`Missing constellation segment star for ${definition.name}: HR ${startHr} -> HR ${endHr}.`);
      }
      return {
        startHr,
        endHr,
        startEci: startStar.eci,
        endEci: endStar.eci,
      };
    });

    const centroidSources = new Map<number, Vec3>();
    centroidSources.set(definition.labelHr, labelStar.eci);
    for (const segment of segments) {
      centroidSources.set(segment.startHr, segment.startEci);
      centroidSources.set(segment.endHr, segment.endEci);
    }

    return {
      abbr: definition.abbr,
      name: definition.name,
      labelHr: definition.labelHr,
      labelOffsetPx: definition.labelOffsetPx,
      labelEci: labelStar.eci,
      centroidEci: normalizeVector(sumVectors([...centroidSources.values()])),
      segments,
    };
  });
}
