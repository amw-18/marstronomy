import type { PlanetKind, Point2, Site, ViewerState } from "./types";

export const DEFAULT_START_UTC_ISO = "2026-04-06T00:00:00Z";

export const DEFAULT_SITE: Site = {
  name: "Olympus Mons",
  latitudeDeg: 18.65,
  longitudeEastDeg: 226.2,
  radiusKm: 3389.5,
};

export const DEFAULT_YAW_DEG = 180;
export const DEFAULT_PITCH_DEG = 20;
export const DEFAULT_FOV_DEG = 75;
export const MIN_FOV_DEG = 50;
export const MAX_FOV_DEG = 95;
export const MIN_PITCH_DEG = -10;
export const MAX_PITCH_DEG = 89.5;
export const RENDER_PIXEL_RATIO_CAP = 2;
export const DEFAULT_SHOW_HUD = true;
export const DEFAULT_SHOW_AZIMUTHAL_GRID = true;
export const DEFAULT_SHOW_EQUATORIAL_GRID = false;
export const DEFAULT_SHOW_ECLIPTIC = true;

export const SPEED_PRESETS = [0, 1, 10, 60, 300, 1800, 7200] as const;
export const PLANET_KINDS: PlanetKind[] = ["mercury", "venus", "earth", "jupiter", "saturn"];
export const STEP_BUTTONS = [
  { label: "-10m", seconds: -600 },
  { label: "+10m", seconds: 600 },
  { label: "-1h", seconds: -3600 },
  { label: "+1h", seconds: 3600 },
] as const;

export const DEFAULT_VIEWER_STATE = (): ViewerState => ({
  simUtcMs: Date.parse(DEFAULT_START_UTC_ISO),
  playing: false,
  speedSecondsPerSecond: 60,
  yawDeg: DEFAULT_YAW_DEG,
  pitchDeg: DEFAULT_PITCH_DEG,
  fovDeg: DEFAULT_FOV_DEG,
  showHud: DEFAULT_SHOW_HUD,
  showAzimuthalGrid: DEFAULT_SHOW_AZIMUTHAL_GRID,
  showEquatorialGrid: DEFAULT_SHOW_EQUATORIAL_GRID,
  showEcliptic: DEFAULT_SHOW_ECLIPTIC,
});

export const SUN_COLOR = "#ffd54a";
export const MERCURY_COLOR = "#d8d2c9";
export const VENUS_COLOR = "#f8e2b3";
export const EARTH_COLOR = "#7fb6ff";
export const JUPITER_COLOR = "#efc18a";
export const SATURN_COLOR = "#e8d6a1";
export const PHOBOS_COLOR = "#ddd7cb";
export const DEIMOS_COLOR = "#aeb9d1";
export const MOON_DARK_COLOR = "#2e333d";

export const PHOBOS_SILHOUETTE_POINTS: Point2[] = [
  [-0.96, -0.14],
  [-0.9, -0.48],
  [-0.66, -0.8],
  [-0.24, -0.96],
  [0.16, -0.88],
  [0.6, -0.74],
  [0.93, -0.32],
  [0.98, 0.1],
  [0.74, 0.5],
  [0.33, 0.8],
  [-0.12, 0.96],
  [-0.54, 0.88],
  [-0.86, 0.56],
  [-1.0, 0.18],
];

export const DEIMOS_SILHOUETTE_POINTS: Point2[] = [
  [-0.94, -0.08],
  [-0.82, -0.46],
  [-0.48, -0.78],
  [-0.06, -0.9],
  [0.34, -0.82],
  [0.74, -0.58],
  [0.92, -0.16],
  [0.88, 0.24],
  [0.6, 0.6],
  [0.2, 0.82],
  [-0.22, 0.86],
  [-0.6, 0.72],
  [-0.86, 0.4],
  [-0.96, 0.04],
];
