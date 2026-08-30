"""Python and JavaScript must compute the same feature vector.

The model is trained in Python and runs in a browser. If the two normalizers
drift apart the accuracy number stays true of a model nobody can use, and no
Python-only test will ever notice. This runs the real web/features.js under
node and compares it to the real ml/features.py, bit for bit within float32.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from features import normalize

JS_SOURCE = os.path.join(HERE, "..", "..", "web", "features.js")

# The payload goes through a file, not argv. Linux caps a single argument at
# 128 KB while macOS allows about 1 MB, so passing JSON on the command line
# works locally and fails only in CI -- which is exactly what happened.
HARNESS = """
import fs from 'node:fs';
import { normalize } from './features.mjs';
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
console.log(JSON.stringify(cases.map(c => Array.from(normalize(c.landmarks, c.handedness)))));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_and_python_agree():
    rng = np.random.default_rng(20260829)
    cases = []
    for i in range(40):
        hand = rng.normal(size=(21, 3)) * rng.uniform(0.02, 0.6) + rng.uniform(-1, 1, size=3)
        cases.append({"landmarks": hand.tolist(), "handedness": "Left" if i % 3 == 0 else "Right"})

    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(JS_SOURCE, os.path.join(tmp, "features.mjs"))
        harness = os.path.join(tmp, "harness.mjs")
        with open(harness, "w") as f:
            f.write(HARNESS)
        payload = os.path.join(tmp, "cases.json")
        with open(payload, "w") as f:
            json.dump(cases, f)
        out = subprocess.run(
            ["node", harness, payload],
            capture_output=True, text=True, check=True, cwd=tmp,
        )
    js = np.array(json.loads(out.stdout), dtype=np.float32)
    py = np.stack([normalize(c["landmarks"], c["handedness"]) for c in cases])

    assert js.shape == py.shape
    assert np.max(np.abs(js - py)) < 1e-5, f"max divergence {np.max(np.abs(js - py))}"
