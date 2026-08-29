// Shared drawing helpers: the MediaPipe hand skeleton, used both for the live
// overlay and for the reference poses in the alphabet chart.

export const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17],
];

export function drawSkeleton(ctx, points, { lineWidth = 3, dotRadius = 4, color = "#7dd3fc", jointColor = "#f8fafc" } = {}) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = lineWidth;
  ctx.strokeStyle = color;
  for (const [a, b] of HAND_CONNECTIONS) {
    ctx.beginPath();
    ctx.moveTo(points[a][0], points[a][1]);
    ctx.lineTo(points[b][0], points[b][1]);
    ctx.stroke();
  }
  ctx.fillStyle = jointColor;
  for (const [x, y] of points) {
    ctx.beginPath();
    ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
    ctx.fill();
  }
}

// Fit a normalized (wrist-centred, unit-scaled) pose into a w x h box.
export function layoutPose(flat, w, h, pad = 0.14) {
  const pts = [];
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (let i = 0; i < 21; i++) {
    const x = flat[i * 3], y = flat[i * 3 + 1];
    pts.push([x, y]);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  const spanX = Math.max(maxX - minX, 1e-6);
  const spanY = Math.max(maxY - minY, 1e-6);
  const scale = Math.min((w * (1 - 2 * pad)) / spanX, (h * (1 - 2 * pad)) / spanY);
  const offX = (w - spanX * scale) / 2 - minX * scale;
  const offY = (h - spanY * scale) / 2 - minY * scale;
  return pts.map(([x, y]) => [x * scale + offX, y * scale + offY]);
}
