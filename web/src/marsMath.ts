import {
  DEIMOS_COLOR,
  DEIMOS_SILHOUETTE_POINTS,
  DEFAULT_SITE,
  MOON_DARK_COLOR,
  PHOBOS_COLOR,
  PHOBOS_SILHOUETTE_POINTS,
  SUN_COLOR,
} from "./constants";
import type {
  MarsSolarData,
  MoonModel,
  MoonPhaseGeometry,
  MovingBody,
  Point2,
  RuntimeStar,
  SceneFrame,
  Site,
  Vec3,
} from "./types";

const TT_MINUS_UTC_SECONDS_DEFAULT = 69.184;

const MARS_POLE_RA_0_DEG = 317.68143;
const MARS_POLE_RA_RATE_DEG_PER_CENTURY = -0.1061;
const MARS_POLE_DEC_0_DEG = 52.8865;
const MARS_POLE_DEC_RATE_DEG_PER_CENTURY = -0.0609;
const MARS_PM_0_DEG = 176.63;
const MARS_PM_RATE_DEG_PER_DAY = 350.89198226;
const JD_J2000 = 2451545.0;
const JULIAN_CENTURY_DAYS = 36525.0;

const MARS_MEAN_HELIOCENTRIC_DISTANCE_AU = 1.52367934;
const MARS_SOL_DURATION_DAYS = 1.0274912517;

const MARS24_PBS_TERMS: ReadonlyArray<[number, number, number]> = [
  [0.0071, 2.2353, 49.409],
  [0.0057, 2.7543, 168.173],
  [0.0039, 1.1177, 191.837],
  [0.0037, 15.7866, 21.736],
  [0.0021, 2.1354, 15.704],
  [0.002, 2.4694, 95.528],
  [0.0018, 32.8493, 49.095],
];

const LEAP_SECOND_TABLE: ReadonlyArray<[number, number]> = [
  ["1972-01-01T00:00:00Z", 42.184],
  ["1972-07-01T00:00:00Z", 43.184],
  ["1973-01-01T00:00:00Z", 44.184],
  ["1974-01-01T00:00:00Z", 45.184],
  ["1975-01-01T00:00:00Z", 46.184],
  ["1976-01-01T00:00:00Z", 47.184],
  ["1977-01-01T00:00:00Z", 48.184],
  ["1978-01-01T00:00:00Z", 49.184],
  ["1979-01-01T00:00:00Z", 50.184],
  ["1980-01-01T00:00:00Z", 51.184],
  ["1981-07-01T00:00:00Z", 52.184],
  ["1982-07-01T00:00:00Z", 53.184],
  ["1983-07-01T00:00:00Z", 54.184],
  ["1985-07-01T00:00:00Z", 55.184],
  ["1988-01-01T00:00:00Z", 56.184],
  ["1990-01-01T00:00:00Z", 57.184],
  ["1991-01-01T00:00:00Z", 58.184],
  ["1992-07-01T00:00:00Z", 59.184],
  ["1993-07-01T00:00:00Z", 60.184],
  ["1994-07-01T00:00:00Z", 61.184],
  ["1996-01-01T00:00:00Z", 62.184],
  ["1997-07-01T00:00:00Z", 63.184],
  ["1999-01-01T00:00:00Z", 64.184],
  ["2006-01-01T00:00:00Z", 65.184],
  ["2009-01-01T00:00:00Z", 66.184],
  ["2012-07-01T00:00:00Z", 67.184],
  ["2015-07-01T00:00:00Z", 68.184],
  ["2017-01-01T00:00:00Z", 69.184],
].map(([iso, value]) => [Date.parse(iso), value]);

export const PHOBOS_MODEL: MoonModel = {
  kind: "phobos",
  name: "Phobos",
  orbitalRadiusKm: 9375,
  orbitalPeriodDays: 0.3187,
  phaseAtJ2000Deg: 189.7,
  color: PHOBOS_COLOR,
  symbolSizePx: 8.5,
  triaxialAxesKm: [27, 22, 18],
  shapeId: "phobos-potato-v1",
  silhouettePoints: PHOBOS_SILHOUETTE_POINTS,
};

export const DEIMOS_MODEL: MoonModel = {
  kind: "deimos",
  name: "Deimos",
  orbitalRadiusKm: 23457,
  orbitalPeriodDays: 1.2625,
  phaseAtJ2000Deg: 205,
  color: DEIMOS_COLOR,
  symbolSizePx: 5.4,
  triaxialAxesKm: [15, 12, 11],
  shapeId: "deimos-potato-v1",
  silhouettePoints: DEIMOS_SILHOUETTE_POINTS,
};

export function wrapDegrees(value: number): number {
  return ((value % 360) + 360) % 360;
}

export function wrapDegreesSigned(value: number): number {
  const wrapped = wrapDegrees(value);
  return wrapped >= 180 ? wrapped - 360 : wrapped;
}

export function wrapHours(value: number): number {
  return ((value % 24) + 24) % 24;
}

export function degToRad(value: number): number {
  return (value * Math.PI) / 180;
}

export function radToDeg(value: number): number {
  return (value * 180) / Math.PI;
}

export function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

export function cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

export function vectorNorm(vector: Vec3): number {
  return Math.sqrt(dot(vector, vector));
}

export function normalizeVector(vector: Vec3): Vec3 {
  const length = vectorNorm(vector);
  if (length === 0) {
    throw new Error("Cannot normalize a zero-length vector.");
  }
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

export function scaleVector(vector: Vec3, scale: number): Vec3 {
  return [vector[0] * scale, vector[1] * scale, vector[2] * scale];
}

export function subtractVectors(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

export function addVectors(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function clampUnit(value: number): number {
  return clamp(value, -1, 1);
}

export function vectorFromRaDec(raDeg: number, decDeg: number): Vec3 {
  const ra = degToRad(raDeg);
  const dec = degToRad(decDeg);
  const cosDec = Math.cos(dec);
  return [cosDec * Math.cos(ra), cosDec * Math.sin(ra), Math.sin(dec)];
}

export function bodyVectorFromLatLon(latDeg: number, lonEastDeg: number): Vec3 {
  const lat = degToRad(latDeg);
  const lon = degToRad(lonEastDeg);
  return [
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  ];
}

export function localBasis(site: Site): { east: Vec3; north: Vec3; up: Vec3 } {
  const lat = degToRad(site.latitudeDeg);
  const lon = degToRad(site.longitudeEastDeg);
  const up: Vec3 = [
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  ];
  const east: Vec3 = [-Math.sin(lon), Math.cos(lon), 0];
  const north: Vec3 = [
    -Math.sin(lat) * Math.cos(lon),
    -Math.sin(lat) * Math.sin(lon),
    Math.cos(lat),
  ];
  return { east, north, up };
}

export function vectorToAltAz(vectorBody: Vec3, east: Vec3, north: Vec3, up: Vec3): [number, number] {
  const unit = normalizeVector(vectorBody);
  const eComp = dot(unit, east);
  const nComp = dot(unit, north);
  const uComp = clampUnit(dot(unit, up));
  const altDeg = radToDeg(Math.asin(uComp));
  const azDeg = wrapDegrees(radToDeg(Math.atan2(eComp, nComp)));
  return [altDeg, azDeg];
}

export function altAzFromLocalVector(localVector: Vec3): [number, number] {
  const unit = normalizeVector(localVector);
  const altDeg = radToDeg(Math.asin(clampUnit(unit[2])));
  const azDeg = wrapDegrees(radToDeg(Math.atan2(unit[0], unit[1])));
  return [altDeg, azDeg];
}

export function localVectorFromAltAz(altDeg: number, azDeg: number): Vec3 {
  const alt = degToRad(altDeg);
  const az = degToRad(azDeg);
  const cosAlt = Math.cos(alt);
  return [Math.sin(az) * cosAlt, Math.cos(az) * cosAlt, Math.sin(alt)];
}

export function observerPositionBody(site: Site): Vec3 {
  return scaleVector(bodyVectorFromLatLon(site.latitudeDeg, site.longitudeEastDeg), site.radiusKm);
}

function rotateAboutAxis(vector: Vec3, axisUnit: Vec3, angleDeg: number): Vec3 {
  const angle = degToRad(angleDeg);
  const cosA = Math.cos(angle);
  const sinA = Math.sin(angle);
  const axisDot = dot(axisUnit, vector);
  const axisCross = cross(axisUnit, vector);
  return [
    vector[0] * cosA + axisCross[0] * sinA + axisUnit[0] * axisDot * (1 - cosA),
    vector[1] * cosA + axisCross[1] * sinA + axisUnit[1] * axisDot * (1 - cosA),
    vector[2] * cosA + axisCross[2] * sinA + axisUnit[2] * axisDot * (1 - cosA),
  ];
}

export function utcMsToJdUtc(utcMs: number): number {
  return 2440587.5 + utcMs / 86400000;
}

export function ttMinusUtcSeconds(utcMs: number): number {
  for (let index = LEAP_SECOND_TABLE.length - 1; index >= 0; index -= 1) {
    const [thresholdMs, value] = LEAP_SECOND_TABLE[index];
    if (utcMs >= thresholdMs) {
      return value;
    }
  }
  return TT_MINUS_UTC_SECONDS_DEFAULT;
}

export function utcMsToJdTt(utcMs: number): number {
  return utcMsToJdUtc(utcMs) + ttMinusUtcSeconds(utcMs) / 86400;
}

export function marsOrientation(jdTt: number): [number, number, number] {
  const deltaDays = jdTt - JD_J2000;
  const centuries = deltaDays / JULIAN_CENTURY_DAYS;
  const poleRaDeg = MARS_POLE_RA_0_DEG + MARS_POLE_RA_RATE_DEG_PER_CENTURY * centuries;
  const poleDecDeg = MARS_POLE_DEC_0_DEG + MARS_POLE_DEC_RATE_DEG_PER_CENTURY * centuries;
  const primeMeridianDeg = wrapDegrees(MARS_PM_0_DEG + MARS_PM_RATE_DEG_PER_DAY * deltaDays);
  return [poleRaDeg, poleDecDeg, primeMeridianDeg];
}

export function marsBodyBasis(
  poleRaDeg: number,
  poleDecDeg: number,
  primeMeridianDeg: number,
): [Vec3, Vec3, Vec3] {
  const pole = vectorFromRaDec(poleRaDeg, poleDecDeg);
  const poleRa = degToRad(poleRaDeg);
  const ascendingNode: Vec3 = [-Math.sin(poleRa), Math.cos(poleRa), 0];
  const xBody = rotateAboutAxis(ascendingNode, pole, primeMeridianDeg);
  const yBody = cross(pole, xBody);
  return [xBody, yBody, pole];
}

export function inertialToBody(vectorInertial: Vec3, xBody: Vec3, yBody: Vec3, zBody: Vec3): Vec3 {
  return [
    dot(vectorInertial, xBody),
    dot(vectorInertial, yBody),
    dot(vectorInertial, zBody),
  ];
}

function bodyToLocal(vectorBody: Vec3, east: Vec3, north: Vec3, up: Vec3): Vec3 {
  return [dot(vectorBody, east), dot(vectorBody, north), dot(vectorBody, up)];
}

function projectOntoPlane(vector: Vec3, planeNormalUnit: Vec3): Vec3 {
  const normalScale = dot(vector, planeNormalUnit);
  return [
    vector[0] - normalScale * planeNormalUnit[0],
    vector[1] - normalScale * planeNormalUnit[1],
    vector[2] - normalScale * planeNormalUnit[2],
  ];
}

function moonLocalBasis(positionBodyKm: Vec3): [Vec3, Vec3, Vec3] {
  const localZ = normalizeVector(scaleVector(positionBodyKm, -1));
  const northRef: Vec3 = [0, 0, 1];
  const localX = normalizeVector(cross(northRef, localZ));
  const localY = normalizeVector(cross(localZ, localX));
  return [localX, localY, localZ];
}

function phaseGeometryFromLocalVectors(
  observerFromMoonLocal: Vec3,
  sunFromMoonLocal: Vec3,
  apparentDiameterArcmin: number,
  symbolSizePx: number,
): MoonPhaseGeometry {
  const observerUnit = normalizeVector(observerFromMoonLocal);
  const sunUnit = normalizeVector(sunFromMoonLocal);

  const phaseAngleDeg = radToDeg(Math.acos(clampUnit(dot(observerUnit, sunUnit))));
  const illuminatedFraction = clamp(0.5 * (1 + Math.cos(degToRad(phaseAngleDeg))), 0, 1);

  const upRef: Vec3 = [0, 1, 0];
  let screenUp = projectOntoPlane(upRef, observerUnit);
  if (vectorNorm(screenUp) < 1e-8) {
    screenUp = projectOntoPlane([1, 0, 0], observerUnit);
  }
  screenUp = normalizeVector(screenUp);
  const screenRight = normalizeVector(cross(screenUp, observerUnit));

  let brightAngleDeg = 90;
  let sunProj = projectOntoPlane(sunUnit, observerUnit);
  if (vectorNorm(sunProj) >= 1e-8) {
    sunProj = normalizeVector(sunProj);
    brightAngleDeg = wrapDegrees(
      radToDeg(Math.atan2(dot(sunProj, screenRight), dot(sunProj, screenUp))),
    );
  }

  return {
    phaseAngleDeg,
    illuminatedFraction,
    brightAngleDeg,
    terminatorAngleDeg: wrapDegrees(brightAngleDeg + 90),
    apparentDiameterArcmin,
    resolvedInMainView: symbolSizePx >= 7 && apparentDiameterArcmin >= 6,
  };
}

function apparentDiameterArcmin(diameterKm: number, distanceKm: number): number {
  if (distanceKm <= 0) {
    return 0;
  }
  const halfAngleRad = Math.atan((0.5 * diameterKm) / distanceKm);
  return radToDeg(2 * halfAngleRad) * 60;
}

function computeMoonPhaseGeometry(
  model: MoonModel,
  positionBodyKm: Vec3,
  observerPositionBodyKm: Vec3,
  sunDirectionBodyVector: Vec3,
): MoonPhaseGeometry {
  const observerFromMoonBody = subtractVectors(observerPositionBodyKm, positionBodyKm);
  const [localX, localY, localZ] = moonLocalBasis(positionBodyKm);
  const observerFromMoonLocal: Vec3 = [
    dot(observerFromMoonBody, localX),
    dot(observerFromMoonBody, localY),
    dot(observerFromMoonBody, localZ),
  ];
  const sunFromMoonLocal: Vec3 = [
    dot(sunDirectionBodyVector, localX),
    dot(sunDirectionBodyVector, localY),
    dot(sunDirectionBodyVector, localZ),
  ];
  const apparentArcmin = apparentDiameterArcmin(
    Math.max(model.triaxialAxesKm[1], model.triaxialAxesKm[2]),
    vectorNorm(observerFromMoonBody),
  );
  return phaseGeometryFromLocalVectors(
    observerFromMoonLocal,
    sunFromMoonLocal,
    apparentArcmin,
    model.symbolSizePx,
  );
}

export function moonModelForKind(kind: "phobos" | "deimos"): MoonModel {
  return kind === "phobos" ? PHOBOS_MODEL : DEIMOS_MODEL;
}

export function marsSolarData(jdTt: number, longitudeEastDeg: number): MarsSolarData {
  const deltaDays = jdTt - JD_J2000;
  const meanAnomalyDeg = wrapDegrees(19.3871 + 0.52402073 * deltaDays);
  const alphaFmsDeg = wrapDegrees(270.3871 + 0.524038496 * deltaDays);

  let pbsDeg = 0;
  for (const [amplitude, tau, phi] of MARS24_PBS_TERMS) {
    const argumentDeg = (0.985626 * deltaDays) / tau + phi;
    pbsDeg += amplitude * Math.cos(degToRad(argumentDeg));
  }

  const meanAnomalyRad = degToRad(meanAnomalyDeg);
  const equationOfCenterDeg =
    (10.691 + 3e-7 * deltaDays) * Math.sin(meanAnomalyRad) +
    0.623 * Math.sin(2 * meanAnomalyRad) +
    0.05 * Math.sin(3 * meanAnomalyRad) +
    0.005 * Math.sin(4 * meanAnomalyRad) +
    0.0005 * Math.sin(5 * meanAnomalyRad) +
    pbsDeg;
  const lsDeg = wrapDegrees(alphaFmsDeg + equationOfCenterDeg);
  const lsRad = degToRad(lsDeg);

  const eotDeg = wrapDegreesSigned(
    2.861 * Math.sin(2 * lsRad) -
      0.071 * Math.sin(4 * lsRad) +
      0.002 * Math.sin(6 * lsRad) -
      equationOfCenterDeg,
  );

  const mstHours = wrapHours(
    24 * (((jdTt - 2451549.5) / MARS_SOL_DURATION_DAYS) + 44796 - 0.0009626),
  );

  const longitudeWestDeg = wrapDegrees(360 - longitudeEastDeg);
  const lmstHours = wrapHours(mstHours - longitudeWestDeg / 15);
  const ltstHours = wrapHours(lmstHours + eotDeg / 15);

  const subsolarLongitudeWestDeg = wrapDegrees(mstHours * 15 + eotDeg + 180);
  const subsolarLongitudeEastDeg = wrapDegrees(360 - subsolarLongitudeWestDeg);

  const solarDeclinationDeg = radToDeg(Math.asin(0.42565 * Math.sin(lsRad))) + 0.25 * Math.sin(lsRad);

  const heliocentricDistanceAu =
    MARS_MEAN_HELIOCENTRIC_DISTANCE_AU *
    (1.00436 -
      0.09309 * Math.cos(meanAnomalyRad) -
      0.004336 * Math.cos(2 * meanAnomalyRad) -
      0.00031 * Math.cos(3 * meanAnomalyRad) -
      0.00003 * Math.cos(4 * meanAnomalyRad));

  return {
    jdTt,
    meanAnomalyDeg,
    alphaFmsDeg,
    pbsDeg,
    equationOfCenterDeg,
    lsDeg,
    eotDeg,
    mstHours,
    lmstHours,
    ltstHours,
    subsolarLongitudeWestDeg,
    subsolarLongitudeEastDeg,
    solarDeclinationDeg,
    heliocentricDistanceAu,
  };
}

export function sunDirectionBody(solarData: MarsSolarData): Vec3 {
  return bodyVectorFromLatLon(
    solarData.solarDeclinationDeg,
    solarData.subsolarLongitudeEastDeg,
  );
}

export function sunSymbolSizePx(heliocentricDistanceAu: number): number {
  return clamp(20 * (MARS_MEAN_HELIOCENTRIC_DISTANCE_AU / heliocentricDistanceAu), 17, 23.5);
}

function moonRelativeRateDegPerDay(model: MoonModel): number {
  return 360 / model.orbitalPeriodDays - MARS_PM_RATE_DEG_PER_DAY;
}

export function moonBodyPosition(model: MoonModel, jdTt: number): [Vec3, number] {
  const deltaDays = jdTt - JD_J2000;
  const lonEastDeg = wrapDegrees(model.phaseAtJ2000Deg + moonRelativeRateDegPerDay(model) * deltaDays);
  const position = scaleVector(bodyVectorFromLatLon(0, lonEastDeg), model.orbitalRadiusKm);
  return [position, lonEastDeg];
}

export function starOpacityFromSunAltitude(sunAltDeg: number): number {
  if (sunAltDeg <= -18) {
    return 1;
  }
  if (sunAltDeg >= 12) {
    return 0.08;
  }
  const t = clamp((sunAltDeg + 18) / 30, 0, 1);
  const eased = t * t * (3 - 2 * t);
  return 1 - 0.92 * eased;
}

export function moonOpacityFromSunAltitude(sunAltDeg: number): number {
  if (sunAltDeg <= -18) {
    return 1;
  }
  if (sunAltDeg >= 12) {
    return 0.4;
  }
  const t = clamp((sunAltDeg + 18) / 30, 0, 1);
  const eased = t * t * (3 - 2 * t);
  return 1 - 0.6 * eased;
}

export function markerSizeForMagnitude(vmag: number): number {
  return clamp(8 * Math.pow(10, -0.18 * (vmag + 1)), 0.8, 7.5);
}

export function moonPixelAxes(model: MoonModel, radiusPx: number): [number, number] {
  const faceOnAxes: [number, number] = [model.triaxialAxesKm[1], model.triaxialAxesKm[2]];
  const maxAxisKm = Math.max(faceOnAxes[0], faceOnAxes[1]);
  return [radiusPx * (faceOnAxes[0] / maxAxisKm), radiusPx * (faceOnAxes[1] / maxAxisKm)];
}

export function unitPhasePolygonPoints(
  phaseAngleDeg: number,
  brightAngleDeg: number,
  sampleCount = 48,
): Point2[] {
  const clampedPhase = clamp(phaseAngleDeg, 0, 180);
  const sign = clampedPhase <= 90 ? -1 : 1;
  const cosineTerm = Math.abs(Math.cos(degToRad(clampedPhase)));

  const points: Point2[] = [];
  for (let sample = 0; sample <= sampleCount; sample += 1) {
    const yCoord = -1 + (2 * sample) / sampleCount;
    const xCoord = sign * cosineTerm * Math.sqrt(Math.max(0, 1 - yCoord * yCoord));
    points.push([xCoord, yCoord]);
  }

  for (let sample = 0; sample <= sampleCount; sample += 1) {
    const theta = Math.PI / 2 - (Math.PI * sample) / sampleCount;
    points.push([Math.cos(theta), Math.sin(theta)]);
  }

  const theta = degToRad(90 - brightAngleDeg);
  const cosTheta = Math.cos(theta);
  const sinTheta = Math.sin(theta);
  return points.map(([pointX, pointY]) => [
    pointX * cosTheta - pointY * sinTheta,
    pointX * sinTheta + pointY * cosTheta,
  ]);
}

function buildSunBody(solarData: MarsSolarData, east: Vec3, north: Vec3, up: Vec3): MovingBody {
  const direction = sunDirectionBody(solarData);
  const localVector = bodyToLocal(direction, east, north, up);
  const [altDeg, azDeg] = altAzFromLocalVector(localVector);
  return {
    kind: "sun",
    name: "Sun",
    altDeg,
    azDeg,
    visible: altDeg > 0,
    symbolSizePx: sunSymbolSizePx(solarData.heliocentricDistanceAu),
    color: SUN_COLOR,
    distanceAu: solarData.heliocentricDistanceAu,
    localVector,
  };
}

function buildMoonBody(
  model: MoonModel,
  jdTt: number,
  site: Site,
  east: Vec3,
  north: Vec3,
  up: Vec3,
  sunDirectionBodyVector: Vec3,
): MovingBody {
  const [positionBody] = moonBodyPosition(model, jdTt);
  const observer = observerPositionBody(site);
  const topocentric = subtractVectors(positionBody, observer);
  const [altDeg, azDeg] = vectorToAltAz(topocentric, east, north, up);
  const phaseGeometry = computeMoonPhaseGeometry(
    model,
    positionBody,
    observer,
    sunDirectionBodyVector,
  );
  const localVector = bodyToLocal(topocentric, east, north, up);

  return {
    kind: model.kind,
    name: model.name,
    altDeg,
    azDeg,
    visible: altDeg > 0,
    symbolSizePx: model.symbolSizePx,
    color: model.color,
    distanceKm: vectorNorm(topocentric),
    phaseAngleDeg: phaseGeometry.phaseAngleDeg,
    illuminatedFraction: phaseGeometry.illuminatedFraction,
    terminatorAngleDeg: phaseGeometry.terminatorAngleDeg,
    apparentDiameterArcmin: phaseGeometry.apparentDiameterArcmin,
    resolvedInMainView: phaseGeometry.resolvedInMainView,
    shapeId: model.shapeId,
    brightAngleDeg: phaseGeometry.brightAngleDeg,
    localVector,
  };
}

export function buildInertialToLocalRows(jdTt: number, site: Site): [Vec3, Vec3, Vec3] {
  const [poleRaDeg, poleDecDeg, primeMeridianDeg] = marsOrientation(jdTt);
  const [xBody, yBody, zBody] = marsBodyBasis(poleRaDeg, poleDecDeg, primeMeridianDeg);
  const { east, north, up } = localBasis(site);

  const composeRow = (bodyVector: Vec3): Vec3 => [
    bodyVector[0] * xBody[0] + bodyVector[1] * yBody[0] + bodyVector[2] * zBody[0],
    bodyVector[0] * xBody[1] + bodyVector[1] * yBody[1] + bodyVector[2] * zBody[1],
    bodyVector[0] * xBody[2] + bodyVector[1] * yBody[2] + bodyVector[2] * zBody[2],
  ];

  return [composeRow(east), composeRow(north), composeRow(up)];
}

export function inertialToLocalVector(vectorInertial: Vec3, rows: [Vec3, Vec3, Vec3]): Vec3 {
  return [dot(vectorInertial, rows[0]), dot(vectorInertial, rows[1]), dot(vectorInertial, rows[2])];
}

export function sceneFrameForTime(utcMs: number, site: Site = DEFAULT_SITE): SceneFrame {
  const jdTt = utcMsToJdTt(utcMs);
  const solarData = marsSolarData(jdTt, site.longitudeEastDeg);
  const { east, north, up } = localBasis(site);
  const sunDirection = sunDirectionBody(solarData);
  const sun = buildSunBody(solarData, east, north, up);
  const phobos = buildMoonBody(PHOBOS_MODEL, jdTt, site, east, north, up, sunDirection);
  const deimos = buildMoonBody(DEIMOS_MODEL, jdTt, site, east, north, up, sunDirection);

  return {
    solarData,
    starOpacity: starOpacityFromSunAltitude(sun.altDeg),
    moonOpacity: moonOpacityFromSunAltitude(sun.altDeg),
    inertialToLocalRows: buildInertialToLocalRows(jdTt, site),
    bodies: { sun, phobos, deimos },
  };
}

export function formatMarsClock(hoursValue: number): string {
  const hoursWrapped = wrapHours(hoursValue);
  const totalSeconds = Math.floor(hoursWrapped * 3600 + 0.5);
  const hours = Math.floor(totalSeconds / 3600) % 24;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const seconds = totalSeconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(
    seconds,
  ).padStart(2, "0")}`;
}

export function formatUtcInputValue(utcMs: number): string {
  return new Date(utcMs).toISOString().slice(0, 19);
}

export function parseUtcInputValue(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const parsed = Date.parse(`${normalized}Z`);
  return Number.isFinite(parsed) ? parsed : null;
}

export function visibleStarCountAtTime(stars: RuntimeStar[], utcMs: number, site: Site = DEFAULT_SITE): number {
  const rows = sceneFrameForTime(utcMs, site).inertialToLocalRows;
  let count = 0;
  for (const star of stars) {
    const local = inertialToLocalVector(star.eci, rows);
    if (local[2] > 0) {
      count += 1;
    }
  }
  return count;
}

export { DEFAULT_SITE, MOON_DARK_COLOR };
