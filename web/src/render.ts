import { MOON_DARK_COLOR } from "./constants";
import {
  clamp,
  cross,
  dot,
  inertialToLocalVector,
  localVectorFromAltAz,
  markerSizeForMagnitude,
  moonModelForKind,
  moonPixelAxes,
  normalizeVector,
  scaleVector,
  unitPhasePolygonPoints,
  vectorNorm,
} from "./marsMath";
import type { MovingBody, Point2, RenderStats, RuntimeStar, SceneFrame, Vec3, ViewerState } from "./types";

interface ProjectedPoint {
  x: number;
  y: number;
  depth: number;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hexToRgb(value: string): [number, number, number] {
  const normalized = value.replace("#", "");
  return [
    Number.parseInt(normalized.slice(0, 2), 16),
    Number.parseInt(normalized.slice(2, 4), 16),
    Number.parseInt(normalized.slice(4, 6), 16),
  ];
}

function rgbToCss(red: number, green: number, blue: number): string {
  return `rgb(${Math.round(red)} ${Math.round(green)} ${Math.round(blue)})`;
}

function mixColor(start: string, end: string, t: number): string {
  const startRgb = hexToRgb(start);
  const endRgb = hexToRgb(end);
  return rgbToCss(
    lerp(startRgb[0], endRgb[0], t),
    lerp(startRgb[1], endRgb[1], t),
    lerp(startRgb[2], endRgb[2], t),
  );
}

function buildCameraBasis(state: ViewerState): { forward: Vec3; right: Vec3; up: Vec3 } {
  const yaw = (state.yawDeg * Math.PI) / 180;
  const pitch = (state.pitchDeg * Math.PI) / 180;
  const forward: Vec3 = [
    Math.sin(yaw) * Math.cos(pitch),
    Math.cos(yaw) * Math.cos(pitch),
    Math.sin(pitch),
  ];
  const right: Vec3 = normalizeVector([Math.cos(yaw), -Math.sin(yaw), 0]);
  const up = normalizeVector(cross(right, forward));
  return { forward, right, up };
}

function projectLocalVector(
  localVector: Vec3,
  state: ViewerState,
  width: number,
  height: number,
): ProjectedPoint | null {
  const { forward, right, up } = buildCameraBasis(state);
  const x = dot(localVector, right);
  const y = dot(localVector, up);
  const z = dot(localVector, forward);
  if (z <= 0.01) {
    return null;
  }
  const focalLength = height * 0.5 / Math.tan((state.fovDeg * Math.PI) / 360);
  return {
    x: width * 0.5 + (x / z) * focalLength,
    y: height * 0.5 - (y / z) * focalLength,
    depth: z,
  };
}

function drawTextHalo(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  color: string,
  font: string,
): void {
  ctx.save();
  ctx.font = font;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.strokeStyle = "rgba(5, 8, 16, 0.86)";
  ctx.lineWidth = 4;
  ctx.strokeText(text, x, y);
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
  ctx.restore();
}

function traceSmoothClosedPath(
  ctx: CanvasRenderingContext2D,
  points: Point2[],
  centerX: number,
  centerY: number,
  scaleX: number,
  scaleY: number,
): void {
  if (points.length === 0) {
    return;
  }
  const transformed = points.map(([pointX, pointY]) => [
    centerX + pointX * scaleX,
    centerY - pointY * scaleY,
  ] as Point2);
  const midpoint = (a: Point2, b: Point2): Point2 => [(a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5];
  const start = midpoint(transformed[transformed.length - 1], transformed[0]);
  ctx.beginPath();
  ctx.moveTo(start[0], start[1]);
  transformed.forEach((point, index) => {
    const nextPoint = transformed[(index + 1) % transformed.length];
    const segmentMidpoint = midpoint(point, nextPoint);
    ctx.quadraticCurveTo(point[0], point[1], segmentMidpoint[0], segmentMidpoint[1]);
  });
  ctx.closePath();
}

function tracePolygonPath(
  ctx: CanvasRenderingContext2D,
  points: Point2[],
  centerX: number,
  centerY: number,
  scaleX: number,
  scaleY: number,
): void {
  if (points.length === 0) {
    return;
  }
  ctx.beginPath();
  ctx.moveTo(centerX + points[0][0] * scaleX, centerY - points[0][1] * scaleY);
  for (let index = 1; index < points.length; index += 1) {
    ctx.lineTo(centerX + points[index][0] * scaleX, centerY - points[index][1] * scaleY);
  }
  ctx.closePath();
}

function drawResolvedMoonGlyph(
  ctx: CanvasRenderingContext2D,
  body: MovingBody,
  centerX: number,
  centerY: number,
  radiusPx: number,
  opacity: number,
): void {
  if (body.kind === "sun") {
    return;
  }
  const model = moonModelForKind(body.kind);
  const [scaleX, scaleY] = moonPixelAxes(model, radiusPx);
  traceSmoothClosedPath(ctx, model.silhouettePoints, centerX, centerY, scaleX, scaleY);
  ctx.save();
  ctx.fillStyle = MOON_DARK_COLOR;
  ctx.globalAlpha = Math.max(0.42, opacity * 0.9);
  ctx.fill();
  ctx.restore();

  if ((body.illuminatedFraction ?? 0) > 0.001) {
    ctx.save();
    traceSmoothClosedPath(ctx, model.silhouettePoints, centerX, centerY, scaleX, scaleY);
    ctx.clip();
    tracePolygonPath(
      ctx,
      unitPhasePolygonPoints(body.phaseAngleDeg ?? 180, body.brightAngleDeg ?? 90),
      centerX,
      centerY,
      scaleX,
      scaleY,
    );
    ctx.fillStyle = body.color;
    ctx.globalAlpha = opacity;
    ctx.fill();
    ctx.restore();
  }

  traceSmoothClosedPath(ctx, model.silhouettePoints, centerX, centerY, scaleX, scaleY);
  ctx.save();
  ctx.strokeStyle = "rgba(220, 229, 244, 0.92)";
  ctx.lineWidth = Math.max(0.85, radiusPx * 0.1);
  ctx.globalAlpha = Math.min(1, opacity + 0.12);
  ctx.stroke();
  ctx.restore();
}

function drawUnresolvedMoonGlyph(
  ctx: CanvasRenderingContext2D,
  body: MovingBody,
  centerX: number,
  centerY: number,
  radiusPx: number,
  opacity: number,
): void {
  const brightAngle = ((body.brightAngleDeg ?? 90) * Math.PI) / 180;
  const highlightDx = Math.sin(brightAngle) * radiusPx * 0.34;
  const highlightDy = -Math.cos(brightAngle) * radiusPx * 0.34;
  const illuminatedFraction = body.illuminatedFraction ?? 0.5;
  const highlightRadius = Math.max(0.9, radiusPx * (0.34 + 0.12 * illuminatedFraction));
  const highlightOpacity = opacity * (0.18 + 0.72 * illuminatedFraction);

  ctx.save();
  ctx.fillStyle = body.color;
  ctx.globalAlpha = 0.07 * opacity;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radiusPx * 1.28, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.save();
  ctx.fillStyle = MOON_DARK_COLOR;
  ctx.strokeStyle = "rgba(219, 226, 239, 0.9)";
  ctx.lineWidth = 1.1;
  ctx.globalAlpha = opacity;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radiusPx, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();

  ctx.save();
  ctx.fillStyle = body.color;
  ctx.globalAlpha = highlightOpacity;
  ctx.beginPath();
  ctx.arc(centerX + highlightDx, centerY + highlightDy, highlightRadius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawSunGlyph(
  ctx: CanvasRenderingContext2D,
  body: MovingBody,
  centerX: number,
  centerY: number,
  radiusPx: number,
): void {
  ctx.save();
  const glow = ctx.createRadialGradient(centerX, centerY, radiusPx * 0.2, centerX, centerY, radiusPx * 2.8);
  glow.addColorStop(0, "rgba(255, 222, 120, 0.8)");
  glow.addColorStop(1, "rgba(255, 222, 120, 0)");
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radiusPx * 2.8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = body.color;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radiusPx, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255, 247, 197, 0.96)";
  ctx.lineWidth = Math.max(1.2, radiusPx * 0.14);
  ctx.stroke();
  ctx.restore();
}

function drawSkyBackground(ctx: CanvasRenderingContext2D, width: number, height: number, sunAltDeg: number): void {
  const dayFactor = clamp((sunAltDeg + 8) / 32, 0, 1);
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, mixColor("#050915", "#8a4e2e", dayFactor * 0.65));
  gradient.addColorStop(0.55, mixColor("#09101f", "#c47a43", dayFactor * 0.78));
  gradient.addColorStop(1, mixColor("#121a2c", "#e1ad73", dayFactor));
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.save();
  ctx.fillStyle = "rgba(3, 6, 12, 0.22)";
  ctx.fillRect(0, 0, width, height);
  ctx.restore();
}

function drawHorizon(
  ctx: CanvasRenderingContext2D,
  state: ViewerState,
  width: number,
  height: number,
): void {
  const projected: ProjectedPoint[] = [];
  for (let az = 0; az <= 360; az += 2) {
    const point = projectLocalVector(localVectorFromAltAz(0, az), state, width, height);
    if (point) {
      projected.push(point);
    }
  }

  if (projected.length < 2) {
    return;
  }

  projected.sort((a, b) => a.x - b.x);
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(projected[0].x, height);
  for (const point of projected) {
    ctx.lineTo(point.x, point.y);
  }
  ctx.lineTo(projected[projected.length - 1].x, height);
  ctx.closePath();
  const ground = ctx.createLinearGradient(0, projected[0].y, 0, height);
  ground.addColorStop(0, "rgba(40, 25, 20, 0.25)");
  ground.addColorStop(1, "rgba(21, 12, 10, 0.92)");
  ctx.fillStyle = ground;
  ctx.fill();
  ctx.restore();

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(projected[0].x, projected[0].y);
  for (const point of projected.slice(1)) {
    ctx.lineTo(point.x, point.y);
  }
  ctx.strokeStyle = "rgba(233, 192, 151, 0.72)";
  ctx.lineWidth = 1.4;
  ctx.stroke();
  ctx.restore();
}

function drawCardinalMarkers(
  ctx: CanvasRenderingContext2D,
  state: ViewerState,
  width: number,
  height: number,
): void {
  const markers = [
    { label: "N", az: 0 },
    { label: "E", az: 90 },
    { label: "S", az: 180 },
    { label: "W", az: 270 },
  ];

  markers.forEach((marker) => {
    const base = projectLocalVector(localVectorFromAltAz(0, marker.az), state, width, height);
    const labelPoint = projectLocalVector(localVectorFromAltAz(5, marker.az), state, width, height);
    if (!base || !labelPoint) {
      return;
    }
    if (base.x < -60 || base.x > width + 60 || base.y < -60 || base.y > height + 60) {
      return;
    }
    ctx.save();
    ctx.strokeStyle = "rgba(228, 235, 248, 0.82)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(base.x, base.y);
    ctx.lineTo(labelPoint.x, labelPoint.y);
    ctx.stroke();
    ctx.restore();
    drawTextHalo(ctx, marker.label, labelPoint.x, labelPoint.y - 10, "#f4f7ff", "600 13px 'Trebuchet MS', sans-serif");
  });
}

function drawStars(
  ctx: CanvasRenderingContext2D,
  stars: RuntimeStar[],
  frame: SceneFrame,
  state: ViewerState,
  width: number,
  height: number,
): number {
  const fovScale = 75 / state.fovDeg;
  let visibleCount = 0;
  for (const star of stars) {
    const local = inertialToLocalVector(star.eci, frame.inertialToLocalRows);
    if (local[2] <= 0) {
      continue;
    }
    const projected = projectLocalVector(local, state, width, height);
    if (!projected) {
      continue;
    }
    if (projected.x < -24 || projected.x > width + 24 || projected.y < -24 || projected.y > height + 24) {
      continue;
    }
    const size = markerSizeForMagnitude(star.m) * Math.pow(fovScale, 0.58);
    const alpha = clamp(frame.starOpacity * (0.35 + size / 8), 0.06, 1);
    ctx.save();
    ctx.fillStyle = star.rgb;
    ctx.globalAlpha = alpha;
    if (size < 1.8) {
      ctx.fillRect(projected.x - size * 0.5, projected.y - size * 0.5, size, size);
    } else {
      ctx.beginPath();
      ctx.arc(projected.x, projected.y, size * 0.5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    visibleCount += 1;
  }
  return visibleCount;
}

function drawMovingBodies(
  ctx: CanvasRenderingContext2D,
  frame: SceneFrame,
  state: ViewerState,
  width: number,
  height: number,
): RenderStats {
  const fovScale = 75 / state.fovDeg;
  const bodies = [frame.bodies.sun, frame.bodies.phobos, frame.bodies.deimos];
  let bodiesDrawn = 0;

  for (const body of bodies) {
    if (!body.visible) {
      continue;
    }
    const projected = projectLocalVector(body.localVector, state, width, height);
    if (!projected) {
      continue;
    }
    if (projected.x < -80 || projected.x > width + 80 || projected.y < -80 || projected.y > height + 80) {
      continue;
    }

    if (body.kind === "sun") {
      drawSunGlyph(ctx, body, projected.x, projected.y, body.symbolSizePx * 0.5 * fovScale);
    } else {
      const opacity = frame.moonOpacity;
      const radius = Math.max(2.8, body.symbolSizePx * 0.5 * fovScale);
      if (body.resolvedInMainView) {
        drawResolvedMoonGlyph(ctx, body, projected.x, projected.y, radius, opacity);
      } else {
        drawUnresolvedMoonGlyph(ctx, body, projected.x, projected.y, radius, opacity);
      }
    }

    drawTextHalo(
      ctx,
      body.name,
      projected.x,
      projected.y - Math.max(18, body.symbolSizePx * 0.9 * fovScale),
      "#eef3ff",
      "600 12px 'Trebuchet MS', sans-serif",
    );
    bodiesDrawn += 1;
  }

  return {
    visibleStarCount: 0,
    bodiesDrawn,
    sunVisible: frame.bodies.sun.visible,
    phobosVisible: frame.bodies.phobos.visible,
    deimosVisible: frame.bodies.deimos.visible,
  };
}

export function renderMoonInset(canvas: HTMLCanvasElement, body: MovingBody): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Could not acquire a 2D context for the moon inset canvas.");
  }

  const size = Math.max(1, Math.floor(canvas.clientWidth || canvas.width || 80));
  if (canvas.width !== size || canvas.height !== size) {
    canvas.width = size;
    canvas.height = size;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const center = canvas.width * 0.5;
  const radius = body.kind === "phobos" ? canvas.width * 0.28 : canvas.width * 0.22;
  const opacity = body.visible ? 1 : 0.45;
  drawResolvedMoonGlyph(ctx, body, center, center, radius, opacity);
}

export class SkyRenderer {
  readonly canvas: HTMLCanvasElement;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
  }

  private getContext(): CanvasRenderingContext2D {
    const ctx = this.canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Could not acquire a 2D context for the main sky canvas.");
    }
    return ctx;
  }

  resize(pixelRatioCap = 2): void {
    const rect = this.canvas.getBoundingClientRect();
    const cssWidth = Math.max(960, Math.round(rect.width || window.innerWidth || 1280));
    const cssHeight = Math.max(540, Math.round(rect.height || window.innerHeight || 720));
    const dpr = Math.min(window.devicePixelRatio || 1, pixelRatioCap);
    const nextWidth = Math.round(cssWidth * dpr);
    const nextHeight = Math.round(cssHeight * dpr);

    if (this.canvas.width !== nextWidth || this.canvas.height !== nextHeight) {
      this.canvas.width = nextWidth;
      this.canvas.height = nextHeight;
    }
  }

  render(frame: SceneFrame, stars: RuntimeStar[], state: ViewerState): RenderStats {
    this.resize();
    const ctx = this.getContext();
    const width = this.canvas.width;
    const height = this.canvas.height;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);

    drawSkyBackground(ctx, width, height, frame.bodies.sun.altDeg);
    drawHorizon(ctx, state, width, height);
    drawCardinalMarkers(ctx, state, width, height);
    const visibleStarCount = drawStars(ctx, stars, frame, state, width, height);
    const bodyStats = drawMovingBodies(ctx, frame, state, width, height);

    return {
      visibleStarCount,
      bodiesDrawn: bodyStats.bodiesDrawn,
      sunVisible: bodyStats.sunVisible,
      phobosVisible: bodyStats.phobosVisible,
      deimosVisible: bodyStats.deimosVisible,
    };
  }
}
