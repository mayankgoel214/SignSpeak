"""Landmark -> feature vector.

This is the contract between training and the browser. `web/features.js` is a
line-for-line port and `tests/test_feature_parity.py` fails if the two ever
disagree, because a feature bug that only exists on one side of the wire is
invisible to a Python-only test suite.

The transform exists to remove everything about a hand that is not its shape:
where it is in frame, how big it is, how it is rotated, and which hand it is.
What survives is the pose, which is the only thing a letter is.
"""

import numpy as np

WRIST = 0
MIDDLE_MCP = 9

NUM_LANDMARKS = 21
FEATURE_DIM = NUM_LANDMARKS * 3


def normalize(landmarks, handedness="Right"):
    """landmarks: (21, 3) array in MediaPipe image coordinates.

    Returns a (63,) float32 feature vector.
    """
    pts = np.asarray(landmarks, dtype=np.float64).reshape(NUM_LANDMARKS, 3).copy()

    # Left hands are mirrored onto the right-hand manifold so that one model
    # serves both. MediaPipe's x axis runs left-to-right in image space, so a
    # sign flip is the whole mirror.
    if str(handedness).lower().startswith("l"):
        pts[:, 0] = -pts[:, 0]

    # 1. Translate: the wrist becomes the origin, removing position in frame.
    pts -= pts[WRIST]

    # 2. Rotate in the image plane so the wrist -> middle-finger-MCP axis points
    #    along -y ("up"). Removes how the wrist happened to be tilted.
    vx, vy = pts[MIDDLE_MCP, 0], pts[MIDDLE_MCP, 1]
    norm = np.hypot(vx, vy)
    if norm > 1e-8:
        cos_t, sin_t = -vy / norm, -vx / norm
        x, y = pts[:, 0].copy(), pts[:, 1].copy()
        pts[:, 0] = cos_t * x - sin_t * y
        pts[:, 1] = sin_t * x + cos_t * y

    # 3. Scale: farthest landmark from the wrist becomes unit distance, removing
    #    how close the hand was to the camera.
    scale = np.max(np.linalg.norm(pts, axis=1))
    if scale > 1e-8:
        pts /= scale

    return pts.reshape(-1).astype(np.float32)
