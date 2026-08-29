"""Train the shipped model on every signer and export it to ONNX.

The accuracy quoted anywhere in this repo comes from ml/evaluate.py, not from
this script. This one exists only to produce the artefact the browser loads;
it is trained on all five signers because a shipped model should use all the
data, and its expected performance on a stranger is the leave-one-signer-out
figure that evaluate.py measured with identical code.

Usage:  python ml/train.py data/landmarks.npz
"""

import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from features import FEATURE_DIM
from model import EPOCHS, SEED, predict, train

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def _verify_onnx(path, model):
    """An exported model that disagrees with the model that was measured is a
    different model. Check it rather than trusting the exporter."""
    import onnxruntime as ort

    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    probe = np.random.default_rng(5).normal(size=(8, FEATURE_DIM)).astype(np.float32)
    got = sess.run(None, {"landmarks": probe})[0]
    with torch.no_grad():
        want = model(torch.from_numpy(probe)).numpy()
    gap = float(np.max(np.abs(got - want)))
    if gap > 1e-4:
        raise SystemExit(f"the ONNX export disagrees with PyTorch by {gap}")
    print(f"onnx export verified against pytorch (max difference {gap:.2e})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz", nargs="?", default=os.path.join(ROOT, "data", "landmarks.npz"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "models"))
    args = ap.parse_args()

    X, y, signers, classes, meta = load(args.npz)
    print(f"training on {len(X)} samples, {len(classes)} classes", flush=True)
    model = train(X, y, len(classes), verbose=True)

    train_acc = float((predict(model, X) == y).mean())
    print(f"accuracy on its own training data {train_acc:.4f} (not a performance figure)")

    os.makedirs(args.outdir, exist_ok=True)
    onnx_path = os.path.join(args.outdir, "signspeak.onnx")
    dummy = torch.zeros(1, FEATURE_DIM, dtype=torch.float32)
    torch.onnx.export(
        model,
        dummy,
        onnx_path,
        input_names=["landmarks"],
        output_names=["logits"],
        dynamic_axes={"landmarks": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        dynamo=False,  # keeps the weights inside the .onnx instead of beside it
    )
    _verify_onnx(onnx_path, model)
    torch.save(model.state_dict(), os.path.join(args.outdir, "signspeak.pt"))

    with open(os.path.join(args.outdir, "labels.json"), "w") as f:
        json.dump([c.upper() for c in classes], f)

    eval_path = os.path.join(ROOT, "eval", "results.json")
    held_out = None
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            held_out = json.load(f).get("signer_independent", {}).get("mean_accuracy")

    with open(os.path.join(args.outdir, "metadata.json"), "w") as f:
        json.dump(
            {
                "input": "63 floats: 21 MediaPipe hand landmarks (x, y, z), wrist-centred, rotation-aligned, scale-normalized",
                "output": f"{len(classes)} logits, argmax over labels.json",
                "trained_on": {
                    "dataset": "Surrey ASL Fingerspelling (Pugeault & Bowden, 2011)",
                    "samples": int(len(X)),
                    "signers": sorted(set(signers)),
                },
                "expected_accuracy_on_a_new_signer": held_out,
                "measured_by": "ml/evaluate.py, leave-one-signer-out; see eval/results.json",
                "seed": SEED,
                "epochs": EPOCHS,
            },
            f,
            indent=2,
        )
    print(f"wrote {onnx_path}")


if __name__ == "__main__":
    main()
