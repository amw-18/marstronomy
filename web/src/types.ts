export type Vec3 = [number, number, number];
export type Point2 = [number, number];
export type GridMode = "none" | "azimuthal" | "equatorial";

export interface RuntimeStar {
  h: number | null;
  n: string;
  m: number;
  rgb: string;
  eci: Vec3;
}

export interface Site {
  name: string;
  latitudeDeg: number;
  longitudeEastDeg: number;
  radiusKm: number;
}

export interface MarsSolarData {
  jdTt: number;
  meanAnomalyDeg: number;
  alphaFmsDeg: number;
  pbsDeg: number;
  equationOfCenterDeg: number;
  lsDeg: number;
  eotDeg: number;
  mstHours: number;
  lmstHours: number;
  ltstHours: number;
  subsolarLongitudeWestDeg: number;
  subsolarLongitudeEastDeg: number;
  solarDeclinationDeg: number;
  heliocentricDistanceAu: number;
}

export interface MoonModel {
  kind: "phobos" | "deimos";
  name: string;
  orbitalRadiusKm: number;
  orbitalPeriodDays: number;
  phaseAtJ2000Deg: number;
  color: string;
  symbolSizePx: number;
  triaxialAxesKm: [number, number, number];
  shapeId: string;
  silhouettePoints: Point2[];
}

export interface MoonPhaseGeometry {
  phaseAngleDeg: number;
  illuminatedFraction: number;
  brightAngleDeg: number;
  terminatorAngleDeg: number;
  apparentDiameterArcmin: number;
  resolvedInMainView: boolean;
}

export interface MovingBody {
  kind: "sun" | "phobos" | "deimos";
  name: string;
  altDeg: number;
  azDeg: number;
  visible: boolean;
  symbolSizePx: number;
  color: string;
  localVector: Vec3;
  distanceKm?: number;
  distanceAu?: number;
  phaseAngleDeg?: number;
  illuminatedFraction?: number;
  terminatorAngleDeg?: number;
  apparentDiameterArcmin?: number;
  resolvedInMainView?: boolean;
  shapeId?: string;
  brightAngleDeg?: number;
}

export interface SceneFrame {
  solarData: MarsSolarData;
  starOpacity: number;
  moonOpacity: number;
  inertialToLocalRows: [Vec3, Vec3, Vec3];
  bodies: {
    sun: MovingBody;
    phobos: MovingBody;
    deimos: MovingBody;
  };
}

export interface MarsCelestialBasis {
  equinox: Vec3;
  equatorialEast: Vec3;
  pole: Vec3;
  eclipticEast: Vec3;
  orbitPole: Vec3;
}

export interface ViewerState {
  simUtcMs: number;
  playing: boolean;
  speedSecondsPerSecond: number;
  yawDeg: number;
  pitchDeg: number;
  fovDeg: number;
  gridMode: GridMode;
  showEcliptic: boolean;
}

export interface RenderStats {
  visibleStarCount: number;
  bodiesDrawn: number;
  sunVisible: boolean;
  phobosVisible: boolean;
  deimosVisible: boolean;
}

export interface AppDebugSnapshot {
  state: ViewerState;
  frame: SceneFrame;
  renderStats: RenderStats;
}
