class MockGradient {
  addColorStop(): void {}
}

class MockCanvasContext2D {
  canvas: HTMLCanvasElement;
  fillStyle = "#000";
  strokeStyle = "#000";
  globalAlpha = 1;
  lineWidth = 1;
  font = "12px sans-serif";
  textAlign: CanvasTextAlign = "start";
  textBaseline: CanvasTextBaseline = "alphabetic";

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
  }

  save(): void {}
  restore(): void {}
  setTransform(): void {}
  clearRect(): void {}
  fillRect(): void {}
  beginPath(): void {}
  moveTo(): void {}
  lineTo(): void {}
  quadraticCurveTo(): void {}
  closePath(): void {}
  fill(): void {}
  stroke(): void {}
  clip(): void {}
  arc(): void {}
  ellipse(): void {}
  strokeText(): void {}
  fillText(): void {}
  createLinearGradient(): MockGradient {
    return new MockGradient();
  }
  createRadialGradient(): MockGradient {
    return new MockGradient();
  }
  measureText(text: string): TextMetrics {
    return {
      width: text.length * 8,
      actualBoundingBoxAscent: 8,
      actualBoundingBoxDescent: 2,
      actualBoundingBoxLeft: 0,
      actualBoundingBoxRight: text.length * 8,
      fontBoundingBoxAscent: 8,
      fontBoundingBoxDescent: 2,
      emHeightAscent: 8,
      emHeightDescent: 2,
      hangingBaseline: 0,
      alphabeticBaseline: 0,
      ideographicBaseline: 0,
    };
  }
}

Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  value(this: HTMLCanvasElement) {
    return new MockCanvasContext2D(this);
  },
});

if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = (callback: FrameRequestCallback) =>
    window.setTimeout(() => callback(performance.now()), 16);
}

if (!window.cancelAnimationFrame) {
  window.cancelAnimationFrame = (id: number) => window.clearTimeout(id);
}
