// Port of ml/features.py. Kept deliberately literal so the two can be read
// side by side; tests/test_feature_parity.py runs this file under node and
// fails if it disagrees with the Python original on random inputs.

export const NUM_LANDMARKS = 21;
export const FEATURE_DIM = NUM_LANDMARKS * 3;

const WRIST = 0;
const MIDDLE_MCP = 9;

export function normalize(landmarks, handedness = "Right") {
  // landmarks: array of 21 {x, y, z} or a flat array of 63 numbers.
  // Three input shapes are accepted: MediaPipe's array of {x, y, z}, an array
  // of [x, y, z] triples, and a flat array of 63 numbers.
  const pts = new Float64Array(FEATURE_DIM);
  const head = landmarks[0];
  if (Array.isArray(head)) {
    for (let i = 0; i < NUM_LANDMARKS; i++) {
      pts[i * 3] = landmarks[i][0];
      pts[i * 3 + 1] = landmarks[i][1];
      pts[i * 3 + 2] = landmarks[i][2];
    }
  } else if (head !== null && typeof head === "object") {
    for (let i = 0; i < NUM_LANDMARKS; i++) {
      pts[i * 3] = landmarks[i].x;
      pts[i * 3 + 1] = landmarks[i].y;
      pts[i * 3 + 2] = landmarks[i].z;
    }
  } else {
    for (let i = 0; i < FEATURE_DIM; i++) pts[i] = landmarks[i];
  }

  if (String(handedness).toLowerCase().startsWith("l")) {
    for (let i = 0; i < NUM_LANDMARKS; i++) pts[i * 3] = -pts[i * 3];
  }

  const ox = pts[WRIST * 3], oy = pts[WRIST * 3 + 1], oz = pts[WRIST * 3 + 2];
  for (let i = 0; i < NUM_LANDMARKS; i++) {
    pts[i * 3] -= ox;
    pts[i * 3 + 1] -= oy;
    pts[i * 3 + 2] -= oz;
  }

  const vx = pts[MIDDLE_MCP * 3], vy = pts[MIDDLE_MCP * 3 + 1];
  const norm = Math.hypot(vx, vy);
  if (norm > 1e-8) {
    const cosT = -vy / norm, sinT = -vx / norm;
    for (let i = 0; i < NUM_LANDMARKS; i++) {
      const x = pts[i * 3], y = pts[i * 3 + 1];
      pts[i * 3] = cosT * x - sinT * y;
      pts[i * 3 + 1] = sinT * x + cosT * y;
    }
  }

  let scale = 0;
  for (let i = 0; i < NUM_LANDMARKS; i++) {
    const d = Math.hypot(pts[i * 3], pts[i * 3 + 1], pts[i * 3 + 2]);
    if (d > scale) scale = d;
  }
  if (scale > 1e-8) {
    for (let i = 0; i < FEATURE_DIM; i++) pts[i] /= scale;
  }

  return Float32Array.from(pts);
}
