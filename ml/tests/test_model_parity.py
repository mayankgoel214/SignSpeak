"""The browser's forward pass must equal PyTorch's.

web/model.js reimplements the network by hand so the page does not have to ship
an inference runtime. That is only defensible if it is checked: this test folds
a freshly initialised network, runs it under node, and compares against torch.
It needs no trained artefact, so it guards the export code itself.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pytest
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from export_web_model import fold
from features import FEATURE_DIM
from model import LandmarkMLP

JS_SOURCE = os.path.join(HERE, "..", "..", "web", "model.js")

# Through a file rather than argv: a folded network is far past Linux's 128 KB
# per-argument limit, which macOS does not enforce.
HARNESS = """
import fs from 'node:fs';
import { Classifier } from './model.mjs';
const [weights, inputs] = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const c = new Classifier(weights);
console.log(JSON.stringify(inputs.map(x => Array.from(c.forward(Float32Array.from(x))))));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_forward_matches_pytorch():
    torch.manual_seed(3)
    n_classes = 24
    model = LandmarkMLP(n_classes)
    # Give batch-norm non-trivial running statistics, so the folding is exercised
    # rather than collapsing to the identity.
    model.train()
    model(torch.randn(64, FEATURE_DIM) * 0.4 + 0.1)
    model.eval()

    weights = {"labels": [chr(97 + i) for i in range(n_classes)], "layers": fold(model)}
    rng = np.random.default_rng(11)
    inputs = (rng.normal(size=(16, FEATURE_DIM)) * 0.5).tolist()

    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(JS_SOURCE, os.path.join(tmp, "model.mjs"))
        harness = os.path.join(tmp, "harness.mjs")
        with open(harness, "w") as f:
            f.write(HARNESS)
        payload = os.path.join(tmp, "payload.json")
        with open(payload, "w") as f:
            json.dump([weights, inputs], f)
        out = subprocess.run(
            ["node", harness, payload],
            capture_output=True, text=True, check=True, cwd=tmp,
        )

    js = np.array(json.loads(out.stdout), dtype=np.float64)
    with torch.no_grad():
        py = model(torch.tensor(inputs, dtype=torch.float32)).numpy().astype(np.float64)

    assert js.shape == py.shape
    # 1e-3 absolute, because export rounds the weights to six decimal places.
    assert np.max(np.abs(js - py)) < 1e-3, f"max divergence {np.max(np.abs(js - py))}"
