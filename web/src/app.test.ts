import { readFileSync } from "node:fs";
import path from "node:path";

import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { createMarsObserverApp } from "./app";
import type { RuntimeStar } from "./types";

const stars = JSON.parse(
  readFileSync(path.resolve(process.cwd(), "public/data/stars.min.json"), "utf8"),
) as RuntimeStar[];

function angularDeltaDegrees(a: number, b: number): number {
  const raw = Math.abs(a - b) % 360;
  return raw > 180 ? 360 - raw : raw;
}

describe("mars observer app", () => {
  let root: HTMLDivElement;

  beforeEach(() => {
    root = document.createElement("div");
    root.style.width = "1280px";
    root.style.height = "720px";
    document.body.appendChild(root);
  });

  afterEach(() => {
    root.remove();
  });

  test("loads and renders visible stars", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });

    const snapshot = app.getDebugSnapshot();
    expect(snapshot.renderStats.visibleStarCount).toBeGreaterThan(40);
    app.destroy();
  });

  test("click-drag updates yaw and pitch", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });
    const canvas = root.querySelector("canvas.viewer-canvas") as HTMLCanvasElement;
    const start = app.getDebugSnapshot().state;

    canvas.dispatchEvent(new MouseEvent("mousedown", { button: 0, clientX: 240, clientY: 220, bubbles: true }));
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 320, clientY: 180, bubbles: true }));
    window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));

    const next = app.getDebugSnapshot().state;
    expect(next.yawDeg).not.toBe(start.yawDeg);
    expect(next.pitchDeg).not.toBe(start.pitchDeg);
    app.destroy();
  });

  test("mouse wheel changes the field of view", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });
    const canvas = root.querySelector("canvas.viewer-canvas") as HTMLCanvasElement;
    const before = app.getDebugSnapshot().state.fovDeg;

    canvas.dispatchEvent(new WheelEvent("wheel", { deltaY: -120, bubbles: true, cancelable: true }));

    const after = app.getDebugSnapshot().state.fovDeg;
    expect(after).toBeLessThan(before);
    app.destroy();
  });

  test("play mode advances the UTC clock", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });
    const start = app.getDebugSnapshot().state.simUtcMs;

    app.setSpeed(60);
    app.setPlaying(true);
    app.advanceForTest(1000);

    const next = app.getDebugSnapshot().state.simUtcMs;
    const utcInput = root.querySelector("input.utc-input") as HTMLInputElement;
    expect(next - start).toBe(60000);
    expect(utcInput.value).toContain("2026-04-06T00:01");
    app.destroy();
  });

  test("grid controls update the viewer state", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });
    const equatorialButton = root.querySelector("[data-grid='equatorial']") as HTMLButtonElement;
    const eclipticButton = root.querySelector("[data-action='toggle-ecliptic']") as HTMLButtonElement;

    equatorialButton.click();
    eclipticButton.click();

    const next = app.getDebugSnapshot().state;
    expect(next.showAzimuthalGrid).toBe(true);
    expect(next.showEquatorialGrid).toBe(true);
    expect(next.showEcliptic).toBe(false);
    app.destroy();
  });

  test("high simulation speed makes Phobos move faster than Deimos", () => {
    const app = createMarsObserverApp(root, {
      stars,
      syncUrl: false,
    });
    const start = app.getDebugSnapshot().frame;

    app.setSpeed(7200);
    app.setPlaying(true);
    app.advanceForTest(10000);

    const next = app.getDebugSnapshot().frame;
    const phobosMotion =
      Math.abs(next.bodies.phobos.altDeg - start.bodies.phobos.altDeg) +
      angularDeltaDegrees(next.bodies.phobos.azDeg, start.bodies.phobos.azDeg);
    const deimosMotion =
      Math.abs(next.bodies.deimos.altDeg - start.bodies.deimos.altDeg) +
      angularDeltaDegrees(next.bodies.deimos.azDeg, start.bodies.deimos.azDeg);

    expect(phobosMotion).toBeGreaterThan(deimosMotion);
    app.destroy();
  });
});
