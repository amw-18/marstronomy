import {
  DEFAULT_FOV_DEG,
  DEFAULT_SHOW_HUD,
  DEFAULT_SHOW_AZIMUTHAL_GRID,
  DEFAULT_SHOW_CONSTELLATIONS,
  DEFAULT_SHOW_ECLIPTIC,
  DEFAULT_SHOW_EQUATORIAL_GRID,
  DEFAULT_SHOW_SOLAR_SCATTERING,
  DEFAULT_PITCH_DEG,
  DEFAULT_START_UTC_ISO,
  DEFAULT_VIEWER_STATE,
  DEFAULT_YAW_DEG,
  MAX_FOV_DEG,
  MAX_PITCH_DEG,
  MIN_FOV_DEG,
  MIN_PITCH_DEG,
} from "./constants";
import { clamp } from "./marsMath";
import type { ViewerState } from "./types";

function maybeNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseLegacyGridMode(value: string | null): "none" | "azimuthal" | "equatorial" | null {
  if (value === "none" || value === "azimuthal" || value === "equatorial") {
    return value;
  }
  return null;
}

function maybeBoolean(value: string | null): boolean | null {
  if (value === null) {
    return null;
  }
  return value !== "0";
}

export function readStateFromSearch(search: string): ViewerState {
  const defaults = DEFAULT_VIEWER_STATE();
  const params = new URLSearchParams(search);

  const utc = params.get("utc");
  const parsedUtc = utc ? Date.parse(utc) : Number.NaN;
  const speed = maybeNumber(params.get("speed"));
  const yaw = maybeNumber(params.get("yaw"));
  const pitch = maybeNumber(params.get("pitch"));
  const fov = maybeNumber(params.get("fov"));
  const hud = maybeBoolean(params.get("hud"));
  const solarScattering = maybeBoolean(params.get("scattering"));
  const legacyGridMode = parseLegacyGridMode(params.get("grid"));
  const azimuthal = maybeBoolean(params.get("azimuthal"));
  const equatorial = maybeBoolean(params.get("equatorial"));
  const ecliptic = maybeBoolean(params.get("ecliptic"));
  const constellations = maybeBoolean(params.get("constellations"));

  const showAzimuthalGrid =
    azimuthal ??
    (legacyGridMode === null
      ? DEFAULT_SHOW_AZIMUTHAL_GRID
      : legacyGridMode === "azimuthal");
  const showEquatorialGrid =
    equatorial ??
    (legacyGridMode === null
      ? DEFAULT_SHOW_EQUATORIAL_GRID
      : legacyGridMode === "equatorial");

  return {
    simUtcMs: Number.isFinite(parsedUtc) ? parsedUtc : Date.parse(DEFAULT_START_UTC_ISO),
    playing: false,
    speedSecondsPerSecond: speed ?? defaults.speedSecondsPerSecond,
    yawDeg: wrapYaw(yaw ?? DEFAULT_YAW_DEG),
    pitchDeg: clamp(pitch ?? DEFAULT_PITCH_DEG, MIN_PITCH_DEG, MAX_PITCH_DEG),
    fovDeg: clamp(fov ?? DEFAULT_FOV_DEG, MIN_FOV_DEG, MAX_FOV_DEG),
    showHud: hud ?? DEFAULT_SHOW_HUD,
    showSolarScattering: solarScattering ?? DEFAULT_SHOW_SOLAR_SCATTERING,
    showAzimuthalGrid,
    showEquatorialGrid,
    showEcliptic: ecliptic ?? DEFAULT_SHOW_ECLIPTIC,
    showConstellations: constellations ?? DEFAULT_SHOW_CONSTELLATIONS,
  };
}

function wrapYaw(value: number): number {
  return ((value % 360) + 360) % 360;
}

export function writeStateToSearch(state: ViewerState): string {
  const params = new URLSearchParams();
  params.set("utc", new Date(state.simUtcMs).toISOString());
  params.set("speed", String(state.speedSecondsPerSecond));
  params.set("yaw", state.yawDeg.toFixed(2));
  params.set("pitch", state.pitchDeg.toFixed(2));
  params.set("fov", state.fovDeg.toFixed(2));
  params.set("hud", state.showHud ? "1" : "0");
  params.set("scattering", state.showSolarScattering ? "1" : "0");
  params.set("azimuthal", state.showAzimuthalGrid ? "1" : "0");
  params.set("equatorial", state.showEquatorialGrid ? "1" : "0");
  params.set("ecliptic", state.showEcliptic ? "1" : "0");
  params.set("constellations", state.showConstellations ? "1" : "0");
  return `?${params.toString()}`;
}
