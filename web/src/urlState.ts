import {
  DEFAULT_FOV_DEG,
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

export function readStateFromSearch(search: string): ViewerState {
  const defaults = DEFAULT_VIEWER_STATE();
  const params = new URLSearchParams(search);

  const utc = params.get("utc");
  const parsedUtc = utc ? Date.parse(utc) : Number.NaN;
  const speed = maybeNumber(params.get("speed"));
  const yaw = maybeNumber(params.get("yaw"));
  const pitch = maybeNumber(params.get("pitch"));
  const fov = maybeNumber(params.get("fov"));

  return {
    simUtcMs: Number.isFinite(parsedUtc) ? parsedUtc : Date.parse(DEFAULT_START_UTC_ISO),
    playing: false,
    speedSecondsPerSecond: speed ?? defaults.speedSecondsPerSecond,
    yawDeg: wrapYaw(yaw ?? DEFAULT_YAW_DEG),
    pitchDeg: clamp(pitch ?? DEFAULT_PITCH_DEG, MIN_PITCH_DEG, MAX_PITCH_DEG),
    fovDeg: clamp(fov ?? DEFAULT_FOV_DEG, MIN_FOV_DEG, MAX_FOV_DEG),
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
  return `?${params.toString()}`;
}
