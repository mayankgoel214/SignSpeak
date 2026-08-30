import { expect } from "@playwright/test";

// Installing a fake camera by assigning navigator.mediaDevices.getUserMedia
// works in Chromium and Firefox and is silently ignored in WebKit, where the
// property is not writable on the instance. A dropped stub is not a visible
// failure: the real camera is used instead, the browser refuses it, and a test
// asserting "permission refused" then PASSES for entirely the wrong reason.
//
// Worse, identity is not proof. Measured in Playwright's WebKit:
// navigator.mediaDevices.getUserMedia === ourFunction is TRUE, and calling it
// still runs the native implementation and rejects with NotAllowedError. So the
// stub also counts its own invocations, and tests assert it was actually
// *called* -- a check no engine can satisfy by accident.
function installer(spec) {
  window.__cameraStub = { installed: false, calls: 0 };

  const make = async () => {
    window.__cameraStub.calls += 1;
    if (spec.reject) {
      const err = new Error(`stubbed ${spec.reject}`);
      err.name = spec.reject;
      throw err;
    }

    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");

    if (spec.deadStream) {
      // frameRate 0 emits a frame only when requestFrame() is called, which it
      // never is: a camera that opens and produces nothing.
      const stream = canvas.captureStream(0);
      window.__stubbedTracks = stream.getTracks();
      return stream;
    }

    const images = await Promise.all(
      (spec.frames || []).map(async (b64) => {
        const img = new Image();
        img.src = `data:image/png;base64,${b64}`;
        await img.decode();
        return img;
      })
    );
    if (typeof window.__index !== "number") window.__index = 0;
    const draw = () => {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const img = window.__index >= 0 ? images[window.__index] : null;
      if (img) {
        const pad = Math.round(Math.max(img.width, img.height) * spec.padRatio);
        const side = Math.max(img.width, img.height) + 2 * pad;
        const scale = Math.min(canvas.width / side, canvas.height / side) * 1.6;
        ctx.drawImage(
          img,
          (canvas.width - img.width * scale) / 2,
          (canvas.height - img.height * scale) / 2,
          img.width * scale,
          img.height * scale
        );
      }
      requestAnimationFrame(draw);
    };
    draw();
    const stream = canvas.captureStream(30);
    window.__stubbedTracks = stream.getTracks();
    return stream;
  };

  try {
    navigator.mediaDevices.getUserMedia = make;
  } catch (err) {
    window.__cameraStub.assignmentThrew = String(err);
  }
  if (navigator.mediaDevices.getUserMedia !== make) {
    try {
      Object.defineProperty(MediaDevices.prototype, "getUserMedia", {
        configurable: true,
        writable: true,
        value: make,
      });
    } catch (err) {
      window.__cameraStub.definePropertyThrew = String(err);
    }
  }
  window.__cameraStub.installed = navigator.mediaDevices.getUserMedia === make;
}

export function installCamera(page, spec) {
  return page.addInitScript(installer, spec);
}

export async function expectCameraStubbed(page) {
  const state = await page.evaluate(() => window.__cameraStub);
  expect(
    state && state.installed,
    `the fake camera was not installed (${JSON.stringify(state)}); ` +
      "any assertion after this would be testing the real camera"
  ).toBe(true);
}

// Call after the page has tried to open the camera. Identity checks can pass on
// an engine that ignores the override at call time, and the resulting test then
// passes against the real camera for the wrong reason.
export async function expectCameraStubWasUsed(page) {
  await expect
    .poll(() => page.evaluate(() => (window.__cameraStub || {}).calls || 0), {
      message: "the page opened a camera that was not the stub",
      timeout: 15_000,
    })
    .toBeGreaterThan(0);
}

// Playwright's WebKit routes getUserMedia natively however the page overrides
// it, and never delivers a canvas capture stream into a <video>. Both were
// measured, not assumed. Every non-camera test still runs there.
export const WEBKIT_CANNOT_FAKE_A_CAMERA =
  "Playwright's WebKit ignores a page-level getUserMedia override at call time " +
  "and cannot pipe a canvas capture stream into a video element";
