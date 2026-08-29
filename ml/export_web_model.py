"""Export the trained network for the browser as folded weights, plus one
representative hand pose per letter.

The browser does not run ONNX Runtime. The network is three fully-connected
layers, so batch-norm is folded into the preceding linear layer at export time
and the whole forward pass becomes forty lines of JavaScript in web/model.js.
That removes a multi-megabyte runtime dependency from a page whose entire model
is 52,000 parameters. ml/tests/test_model_parity.py asserts the JavaScript agrees with
PyTorch, which is the only reason this shortcut is safe.

The prototypes are the medoid landmark pose of each letter, drawn in the UI so
a visitor who does not know the ASL alphabet can see what to do with their hand.
They are derived from the dataset's landmarks, not its images.

Usage:  python ml/export_web_model.py
"""

import json
import os
import sys

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import LandmarkMLP

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def fold(model):
    """Sequential of [Linear, BatchNorm, ReLU, Dropout] blocks -> plain layers."""
    layers, mods = [], list(model.net)
    i = 0
    while i < len(mods):
        m = mods[i]
        assert isinstance(m, nn.Linear), f"unexpected module {m}"
        W = m.weight.detach().numpy().astype(np.float64)
        b = m.bias.detach().numpy().astype(np.float64)
        i += 1
        if i < len(mods) and isinstance(mods[i], nn.BatchNorm1d):
            bn = mods[i]
            s = np.sqrt(bn.running_var.detach().numpy() + bn.eps)
            g = bn.weight.detach().numpy() / s
            b = (b - bn.running_mean.detach().numpy()) * g + bn.bias.detach().numpy()
            W = W * g[:, None]
            i += 1
        relu = i < len(mods) and isinstance(mods[i], nn.ReLU)
        while i < len(mods) and isinstance(mods[i], (nn.ReLU, nn.Dropout)):
            i += 1
        layers.append(
            {
                "in": int(W.shape[1]),
                "out": int(W.shape[0]),
                "w": [round(float(v), 6) for v in W.reshape(-1)],
                "b": [round(float(v), 6) for v in b],
                "relu": bool(relu),
            }
        )
    return layers


def prototypes(X, y, classes):
    """The real sample closest to each class's mean -- an actual observed hand,
    not an average that no hand ever made."""
    out = {}
    for c, name in enumerate(classes):
        members = X[y == c]
        if not len(members):
            continue
        centre = members.mean(axis=0)
        best = members[np.argmin(np.linalg.norm(members - centre, axis=1))]
        out[name.upper()] = [round(float(v), 4) for v in best]
    return out


def main():
    npz = os.path.join(ROOT, "data", "landmarks.npz")
    X, y, _signers, classes, _meta = load(npz)

    model = LandmarkMLP(len(classes))
    model.load_state_dict(torch.load(os.path.join(ROOT, "models", "signspeak.pt")))
    model.eval()

    payload = {
        "labels": [c.upper() for c in classes],
        "layers": fold(model),
        "prototypes": prototypes(X, y, classes),
    }
    out = os.path.join(ROOT, "models", "signspeak.weights.json")
    with open(out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
