"""The artefacts that ship must be the model that was measured.

Three different files claim to be the classifier: signspeak.pt (what evaluate.py
and train.py produce), signspeak.onnx (the portable export) and
signspeak.weights.json (what the browser actually runs). Each is written by a
separate script, so any of them can go stale without a single other test failing
-- and a stale weights.json means the live page runs a model nobody measured
while every number on it stays confidently wrong.

These tests compare the real files on disk, not freshly constructed ones.
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
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(HERE, ".."))

from export_web_model import fold
from features import FEATURE_DIM, normalize
from model import LandmarkMLP

MODELS = os.path.join(ROOT, "models")
PT = os.path.join(MODELS, "signspeak.pt")
ONNX = os.path.join(MODELS, "signspeak.onnx")
WEIGHTS = os.path.join(MODELS, "signspeak.weights.json")
LABELS = os.path.join(MODELS, "labels.json")
METADATA = os.path.join(MODELS, "metadata.json")
RESULTS = os.path.join(ROOT, "eval", "results.json")

JS_MODEL = os.path.join(ROOT, "web", "model.js")
# Through a file rather than argv -- see test_model_parity.py.
HARNESS = """
import fs from 'node:fs';
import { Classifier } from './model.mjs';
const [weights, inputs] = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const c = new Classifier(weights);
console.log(JSON.stringify(inputs.map(x => Array.from(c.forward(Float32Array.from(x))))));
"""


def _need(path):
    if not os.path.exists(path):
        pytest.skip(f"{os.path.relpath(path, ROOT)} missing -- run ml/train.py and ml/export_web_model.py")


@pytest.fixture(scope="module")
def weights():
    _need(WEIGHTS)
    with open(WEIGHTS) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def torch_model(weights):
    _need(PT)
    m = LandmarkMLP(len(weights["labels"]))
    m.load_state_dict(torch.load(PT))
    m.eval()
    return m


@pytest.fixture(scope="module")
def probes():
    rng = np.random.default_rng(4242)
    hands = rng.normal(size=(24, 21, 3)) * 0.25
    return np.stack([normalize(h) for h in hands])


def test_browser_weights_are_this_checkpoint_not_an_older_one(weights, torch_model):
    """Refolds the checkpoint on disk and compares it to the exported JSON. This
    is the test that catches an export that was never re-run."""
    expected = fold(torch_model)
    got = weights["layers"]
    assert len(got) == len(expected)
    for i, (a, b) in enumerate(zip(got, expected)):
        assert (a["in"], a["out"], a["relu"]) == (b["in"], b["out"], b["relu"]), f"layer {i} shape"
        assert np.allclose(a["w"], b["w"], atol=1e-6), f"layer {i} weights differ from the checkpoint"
        assert np.allclose(a["b"], b["b"], atol=1e-6), f"layer {i} biases differ from the checkpoint"


def test_onnx_export_agrees_with_the_checkpoint(torch_model, probes):
    _need(ONNX)
    ort = pytest.importorskip("onnxruntime")
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    got = sess.run(None, {"landmarks": probes.astype(np.float32)})[0]
    with torch.no_grad():
        want = torch_model(torch.from_numpy(probes.astype(np.float32))).numpy()
    assert np.max(np.abs(got - want)) < 1e-4


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_browser_runs_the_same_model_as_pytorch(weights, torch_model, probes):
    """End to end on the real shipped files: the JSON the page fetches, through
    the JavaScript the page loads, against the checkpoint that was measured."""
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(JS_MODEL, os.path.join(tmp, "model.mjs"))
        harness = os.path.join(tmp, "harness.mjs")
        with open(harness, "w") as f:
            f.write(HARNESS)
        payload = os.path.join(tmp, "payload.json")
        with open(payload, "w") as f:
            json.dump([weights, probes.tolist()], f)
        out = subprocess.run(
            ["node", harness, payload],
            capture_output=True, text=True, check=True, cwd=tmp,
        )
    js = np.array(json.loads(out.stdout), dtype=np.float64)
    with torch.no_grad():
        py = torch_model(torch.from_numpy(probes.astype(np.float32))).numpy().astype(np.float64)
    assert np.max(np.abs(js - py)) < 1e-3

    # Agreeing on logits is necessary but not sufficient: the labels must line up
    # too, or the page renders a confident wrong letter.
    assert list(js.argmax(1)) == list(py.argmax(1))


def test_labels_agree_across_every_file_that_carries_them(weights):
    _need(LABELS)
    _need(RESULTS)
    with open(LABELS) as f:
        labels = json.load(f)
    with open(RESULTS) as f:
        classes = [c.upper() for c in json.load(f)["dataset"]["classes"]]

    assert labels == weights["labels"] == classes
    assert labels == sorted(labels), "label order is the argmax index -- it must be the sorted class order"
    assert len(labels) == weights["layers"][-1]["out"]


def test_every_letter_has_a_reference_pose(weights):
    protos = weights["prototypes"]
    assert sorted(protos) == sorted(weights["labels"])
    for label, pose in protos.items():
        assert len(pose) == FEATURE_DIM, label
        pts = np.array(pose).reshape(21, 3)
        # Prototypes are stored already normalized; the page draws them directly.
        assert np.allclose(pts[0], 0, atol=1e-3), f"{label}: wrist is not the origin"
        assert np.isclose(np.max(np.linalg.norm(pts, axis=1)), 1.0, atol=1e-3), f"{label}: not unit-scaled"


def test_a_prototype_classifies_as_its_own_letter(weights, torch_model):
    """A reference pose the model does not itself recognise would be a chart of
    something other than what the model learned."""
    labels = weights["labels"]
    poses = np.array([weights["prototypes"][l] for l in labels], dtype=np.float32)
    with torch.no_grad():
        pred = torch_model(torch.from_numpy(poses)).argmax(1).numpy()
    wrong = [(labels[i], labels[p]) for i, p in enumerate(pred) if labels[i] != labels[p]]
    assert not wrong, f"prototypes misclassified: {wrong}"


def test_metadata_quotes_the_measured_figure(weights):
    _need(METADATA)
    _need(RESULTS)
    with open(METADATA) as f:
        meta = json.load(f)
    with open(RESULTS) as f:
        results = json.load(f)
    assert meta["expected_accuracy_on_a_new_signer"] == pytest.approx(
        results["signer_independent"]["mean_accuracy"], abs=1e-9
    ), "models/metadata.json is quoting an accuracy from a different evaluation run"
    assert meta["trained_on"]["samples"] == results["dataset"]["hands_detected_by_mediapipe"]
