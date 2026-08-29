"""Load the cached landmarks and turn them into model inputs."""

import numpy as np

from features import normalize


def load(npz_path):
    d = np.load(npz_path, allow_pickle=True)
    landmarks = d["landmarks"]
    labels = d["labels"].astype(str)
    signers = d["signers"].astype(str)
    handedness = d["handedness"].astype(str)

    X = np.stack([normalize(landmarks[i], handedness[i]) for i in range(len(landmarks))])
    classes = sorted(set(labels))
    index = {c: i for i, c in enumerate(classes)}
    y = np.array([index[l] for l in labels], dtype=np.int64)

    meta = {
        "n_images_total": int(d["n_images_total"]),
        "n_detected": int(d["n_detected"]),
    }
    return X, y, signers, classes, meta
