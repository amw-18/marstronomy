import {
  DEFAULT_FOV_DEG,
  DEFAULT_PITCH_DEG,
  DEFAULT_VIEWER_STATE,
  DEFAULT_YAW_DEG,
  MAX_FOV_DEG,
  MAX_PITCH_DEG,
  MIN_FOV_DEG,
  MIN_PITCH_DEG,
  RENDER_PIXEL_RATIO_CAP,
  SPEED_PRESETS,
  STEP_BUTTONS,
} from "./constants";
import { formatMarsClock, formatUtcInputValue, parseUtcInputValue, sceneFrameForTime, wrapDegrees } from "./marsMath";
import { SkyRenderer, renderMoonInset } from "./render";
import type { AppDebugSnapshot, GridMode, RenderStats, RuntimeStar, SceneFrame, ViewerState } from "./types";
import { writeStateToSearch } from "./urlState";

interface CreateAppOptions {
  stars: RuntimeStar[];
  initialState?: Partial<ViewerState>;
  syncUrl?: boolean;
}

interface ElementRefs {
  canvas: HTMLCanvasElement;
  utcInput: HTMLInputElement;
  marsClockValue: HTMLElement;
  speedValue: HTMLElement;
  playButton: HTMLButtonElement;
  resetButton: HTMLButtonElement;
  speedButtons: HTMLButtonElement[];
  stepButtons: HTMLButtonElement[];
  gridButtons: HTMLButtonElement[];
  eclipticButton: HTMLButtonElement;
  phobosCanvas: HTMLCanvasElement;
  phobosMeta: HTMLElement;
  deimosCanvas: HTMLCanvasElement;
  deimosMeta: HTMLElement;
}

export class MarsObserverApp {
  private readonly root: HTMLElement;
  private readonly stars: RuntimeStar[];
  private readonly elements: ElementRefs;
  private readonly renderer: SkyRenderer;
  private readonly syncUrl: boolean;

  private state: ViewerState;
  private frame: SceneFrame;
  private renderStats: RenderStats = {
    visibleStarCount: 0,
    bodiesDrawn: 0,
    sunVisible: false,
    phobosVisible: false,
    deimosVisible: false,
  };

  private rafId = 0;
  private lastAnimationMs: number | null = null;
  private needsRender = true;
  private urlSyncTimer = 0;

  private isDragging = false;
  private lastDragX = 0;
  private lastDragY = 0;

  private readonly onResize = () => {
    this.requestRender();
  };

  private readonly onMouseMove = (event: MouseEvent) => {
    if (!this.isDragging) {
      return;
    }
    const deltaX = event.clientX - this.lastDragX;
    const deltaY = event.clientY - this.lastDragY;
    this.lastDragX = event.clientX;
    this.lastDragY = event.clientY;

    this.state.yawDeg = wrapDegrees(this.state.yawDeg - deltaX * 0.16);
    this.state.pitchDeg = Math.max(MIN_PITCH_DEG, Math.min(MAX_PITCH_DEG, this.state.pitchDeg + deltaY * 0.12));
    this.requestRender();
    this.scheduleUrlSync();
  };

  private readonly onMouseUp = () => {
    this.isDragging = false;
    this.root.classList.remove("is-dragging");
  };

  private readonly tick = (timestampMs: number) => {
    if (this.lastAnimationMs === null) {
      this.lastAnimationMs = timestampMs;
    }
    const deltaMs = timestampMs - this.lastAnimationMs;
    this.lastAnimationMs = timestampMs;

    if (this.state.playing && this.state.speedSecondsPerSecond > 0) {
      this.state.simUtcMs += deltaMs * this.state.speedSecondsPerSecond;
      this.needsRender = true;
    }

    if (this.needsRender) {
      this.renderNow();
      this.needsRender = false;
    }

    if (this.state.playing || this.needsRender) {
      this.rafId = window.requestAnimationFrame(this.tick);
      return;
    }

    this.rafId = 0;
    this.lastAnimationMs = null;
  };

  constructor(root: HTMLElement, options: CreateAppOptions) {
    this.root = root;
    this.stars = options.stars;
    this.syncUrl = options.syncUrl ?? true;
    this.root.innerHTML = this.template();
    this.root.classList.add("mars-viewer");
    this.state = {
      ...DEFAULT_VIEWER_STATE(),
      ...options.initialState,
    };

    this.elements = this.collectElements();
    this.renderer = new SkyRenderer(this.elements.canvas);
    this.frame = sceneFrameForTime(this.state.simUtcMs);

    this.bindEvents();
    this.renderNow();
    this.requestRender();
  }

  private template(): string {
    return `
      <canvas class="viewer-canvas"></canvas>
      <section class="hud-panel hud-panel--top hud-panel--meta">
        <div class="hud-copy">
          <p class="eyebrow">Mars Observer</p>
          <h1>Olympus Mons Sky</h1>
          <p class="subtle">Real-time, naked-eye style viewer from the Martian surface.</p>
        </div>
        <div class="meta-grid">
          <label class="field">
            <span>UTC time</span>
            <input class="utc-input" type="datetime-local" step="1" />
          </label>
          <div class="field field--readonly">
            <span>Local true solar time</span>
            <strong data-role="mars-clock">00:00:00</strong>
          </div>
          <div class="field field--readonly">
            <span>Current speed</span>
            <strong data-role="speed-value">60 s/s</strong>
          </div>
          <button class="ghost-button" data-action="reset-view" type="button">Reset view</button>
        </div>
      </section>
      <section class="hud-panel hud-panel--bottom hud-panel--controls">
        <div class="controls-row">
          <button class="primary-button" data-action="toggle-play" type="button">Play</button>
          ${STEP_BUTTONS.map(
            (step) =>
              `<button class="ghost-button" data-step="${step.seconds}" type="button">${step.label}</button>`,
          ).join("")}
        </div>
        <div class="controls-row controls-row--speed">
          ${SPEED_PRESETS.map(
            (speed) =>
              `<button class="speed-chip" data-speed="${speed}" type="button">${speed} s/s</button>`,
          ).join("")}
        </div>
        <div class="controls-row controls-row--projection">
          <span class="controls-label">Grid</span>
          <button class="speed-chip" data-grid="none" type="button">Off</button>
          <button class="speed-chip" data-grid="azimuthal" type="button">Azimuthal</button>
          <button class="speed-chip" data-grid="equatorial" type="button">Equatorial</button>
          <button class="speed-chip" data-action="toggle-ecliptic" type="button">Ecliptic</button>
        </div>
      </section>
      <section class="hud-panel hud-panel--moon">
        <p class="eyebrow">Moon Phases</p>
        <div class="moon-card" data-body="phobos">
          <canvas class="moon-canvas" data-canvas="phobos"></canvas>
          <div class="moon-meta" data-meta="phobos"></div>
        </div>
        <div class="moon-card" data-body="deimos">
          <canvas class="moon-canvas" data-canvas="deimos"></canvas>
          <div class="moon-meta" data-meta="deimos"></div>
        </div>
      </section>
    `;
  }

  private collectElements(): ElementRefs {
    const query = <T extends Element>(selector: string): T => {
      const element = this.root.querySelector<T>(selector);
      if (!element) {
        throw new Error(`Missing required element: ${selector}`);
      }
      return element;
    };

    return {
      canvas: query<HTMLCanvasElement>("canvas.viewer-canvas"),
      utcInput: query<HTMLInputElement>("input.utc-input"),
      marsClockValue: query<HTMLElement>("[data-role='mars-clock']"),
      speedValue: query<HTMLElement>("[data-role='speed-value']"),
      playButton: query<HTMLButtonElement>("[data-action='toggle-play']"),
      resetButton: query<HTMLButtonElement>("[data-action='reset-view']"),
      speedButtons: Array.from(this.root.querySelectorAll<HTMLButtonElement>("[data-speed]")),
      stepButtons: Array.from(this.root.querySelectorAll<HTMLButtonElement>("[data-step]")),
      gridButtons: Array.from(this.root.querySelectorAll<HTMLButtonElement>("[data-grid]")),
      eclipticButton: query<HTMLButtonElement>("[data-action='toggle-ecliptic']"),
      phobosCanvas: query<HTMLCanvasElement>("[data-canvas='phobos']"),
      phobosMeta: query<HTMLElement>("[data-meta='phobos']"),
      deimosCanvas: query<HTMLCanvasElement>("[data-canvas='deimos']"),
      deimosMeta: query<HTMLElement>("[data-meta='deimos']"),
    };
  }

  private bindEvents(): void {
    this.elements.canvas.addEventListener("mousedown", (event) => {
      if (event.button !== 0) {
        return;
      }
      this.isDragging = true;
      this.lastDragX = event.clientX;
      this.lastDragY = event.clientY;
      this.root.classList.add("is-dragging");
    });

    this.elements.canvas.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        this.state.fovDeg = Math.max(
          MIN_FOV_DEG,
          Math.min(MAX_FOV_DEG, this.state.fovDeg + event.deltaY * 0.03),
        );
        this.requestRender();
        this.scheduleUrlSync();
      },
      { passive: false },
    );

    this.elements.playButton.addEventListener("click", () => {
      if (!this.state.playing && this.state.speedSecondsPerSecond === 0) {
        this.state.speedSecondsPerSecond = 1;
      }
      this.state.playing = !this.state.playing;
      this.requestRender();
      this.scheduleUrlSync();
    });

    this.elements.resetButton.addEventListener("click", () => {
      this.state.yawDeg = DEFAULT_YAW_DEG;
      this.state.pitchDeg = DEFAULT_PITCH_DEG;
      this.state.fovDeg = DEFAULT_FOV_DEG;
      this.requestRender();
      this.scheduleUrlSync();
    });

    this.elements.utcInput.addEventListener("change", () => {
      const parsed = parseUtcInputValue(this.elements.utcInput.value);
      if (parsed === null) {
        this.elements.utcInput.value = formatUtcInputValue(this.state.simUtcMs);
        return;
      }
      this.state.simUtcMs = parsed;
      this.requestRender();
      this.scheduleUrlSync();
    });

    this.elements.stepButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const seconds = Number.parseFloat(button.dataset.step ?? "0");
        this.state.simUtcMs += seconds * 1000;
        this.requestRender();
        this.scheduleUrlSync();
      });
    });

    this.elements.speedButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const nextSpeed = Number.parseFloat(button.dataset.speed ?? "0");
        this.state.speedSecondsPerSecond = nextSpeed;
        if (nextSpeed === 0) {
          this.state.playing = false;
        }
        this.requestRender();
        this.scheduleUrlSync();
      });
    });

    this.elements.gridButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const nextGridMode = button.dataset.grid;
        if (
          nextGridMode !== "none" &&
          nextGridMode !== "azimuthal" &&
          nextGridMode !== "equatorial"
        ) {
          return;
        }
        const gridMode: GridMode = nextGridMode;
        this.state.gridMode = gridMode;
        this.requestRender();
        this.scheduleUrlSync();
      });
    });

    this.elements.eclipticButton.addEventListener("click", () => {
      this.state.showEcliptic = !this.state.showEcliptic;
      this.requestRender();
      this.scheduleUrlSync();
    });

    window.addEventListener("mousemove", this.onMouseMove);
    window.addEventListener("mouseup", this.onMouseUp);
    window.addEventListener("resize", this.onResize);
  }

  private updateHud(): void {
    this.elements.utcInput.value = formatUtcInputValue(this.state.simUtcMs);
    this.elements.marsClockValue.textContent = formatMarsClock(this.frame.solarData.ltstHours);
    this.elements.speedValue.textContent = `${this.state.speedSecondsPerSecond} s/s`;
    this.elements.playButton.textContent = this.state.playing ? "Pause" : "Play";

    this.elements.speedButtons.forEach((button) => {
      const speed = Number.parseFloat(button.dataset.speed ?? "0");
      button.classList.toggle("is-active", speed === this.state.speedSecondsPerSecond);
    });

    this.elements.gridButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.grid === this.state.gridMode);
      button.setAttribute("aria-pressed", String(button.dataset.grid === this.state.gridMode));
    });

    this.elements.eclipticButton.classList.toggle("is-active", this.state.showEcliptic);
    this.elements.eclipticButton.setAttribute("aria-pressed", String(this.state.showEcliptic));

    const updateMoonMeta = (body: SceneFrame["bodies"]["phobos"] | SceneFrame["bodies"]["deimos"], element: HTMLElement) => {
      const illumination = Math.round((body.illuminatedFraction ?? 0) * 100);
      element.innerHTML = `
        <strong>${body.name}</strong>
        <span>${illumination}% lit</span>
        <span>alt ${body.altDeg >= 0 ? "+" : ""}${body.altDeg.toFixed(0)}°</span>
      `;
      element.parentElement?.classList.toggle("is-hidden", !body.visible);
    };

    updateMoonMeta(this.frame.bodies.phobos, this.elements.phobosMeta);
    updateMoonMeta(this.frame.bodies.deimos, this.elements.deimosMeta);
  }

  private renderNow(): void {
    this.frame = sceneFrameForTime(this.state.simUtcMs);
    this.renderer.resize(RENDER_PIXEL_RATIO_CAP);
    this.renderStats = this.renderer.render(this.frame, this.stars, this.state);
    renderMoonInset(this.elements.phobosCanvas, this.frame.bodies.phobos);
    renderMoonInset(this.elements.deimosCanvas, this.frame.bodies.deimos);
    this.updateHud();
  }

  private scheduleUrlSync(): void {
    if (!this.syncUrl) {
      return;
    }
    window.clearTimeout(this.urlSyncTimer);
    this.urlSyncTimer = window.setTimeout(() => {
      const nextSearch = writeStateToSearch(this.state);
      window.history.replaceState(null, "", nextSearch);
    }, 120);
  }

  private requestRender(): void {
    this.needsRender = true;
    if (this.rafId === 0) {
      this.rafId = window.requestAnimationFrame(this.tick);
    }
  }

  setPlaying(nextPlaying: boolean): void {
    if (nextPlaying && this.state.speedSecondsPerSecond === 0) {
      this.state.speedSecondsPerSecond = 1;
    }
    this.state.playing = nextPlaying;
    this.requestRender();
  }

  setSpeed(nextSpeed: number): void {
    this.state.speedSecondsPerSecond = nextSpeed;
    if (nextSpeed === 0) {
      this.state.playing = false;
    }
    this.requestRender();
  }

  advanceForTest(realDeltaMs: number): void {
    if (this.state.playing && this.state.speedSecondsPerSecond > 0) {
      this.state.simUtcMs += realDeltaMs * this.state.speedSecondsPerSecond;
    }
    this.renderNow();
  }

  getDebugSnapshot(): AppDebugSnapshot {
    return {
      state: { ...this.state },
      frame: this.frame,
      renderStats: this.renderStats,
    };
  }

  destroy(): void {
    window.cancelAnimationFrame(this.rafId);
    window.clearTimeout(this.urlSyncTimer);
    window.removeEventListener("mousemove", this.onMouseMove);
    window.removeEventListener("mouseup", this.onMouseUp);
    window.removeEventListener("resize", this.onResize);
    this.root.innerHTML = "";
  }
}

export function createMarsObserverApp(root: HTMLElement, options: CreateAppOptions): MarsObserverApp {
  return new MarsObserverApp(root, options);
}
