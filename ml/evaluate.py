"""Produce the accuracy figure, both ways, and write eval/results.json.

Two protocols are run because only the contrast between them is honest.

  random    -- a stratified random split over every sample. The Surrey dataset
               is frames from five continuous recording sessions, so adjacent
               frames are near-duplicates of each other. A random split puts
               near-duplicates on both sides of the boundary and the model is
               partly being asked to recognise images it has already seen.

  signer    -- leave-one-signer-out. Train on four people, test on the fifth,
               five times. No frame of the test person is in training, so this
               is the number that estimates what a stranger's webcam will do.

The gap between the two is the size of the leak, and it is reported.

Usage:  python ml/evaluate.py data/landmarks.npz
"""

import argparse
import json
import os
import sys

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import EPOCHS, SEED, predict, train

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def per_class_accuracy(y_true, y_pred, n_classes):
    acc = {}
    for c in range(n_classes):
        m = y_true == c
        acc[c] = float((y_pred[m] == c).mean()) if m.sum() else None
    return acc


def confusion(y_true, y_pred, n_classes):
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    return cm


def top_confusions(cm, classes, k=8):
    pairs = []
    for i in range(len(classes)):
        row = cm[i].sum()
        for j in range(len(classes)):
            if i != j and cm[i, j] > 0:
                pairs.append(
                    {
                        "true": classes[i],
                        "predicted": classes[j],
                        "count": int(cm[i, j]),
                        "rate": float(cm[i, j] / row) if row else 0.0,
                    }
                )
    pairs.sort(key=lambda p: -p["count"])
    return pairs[:k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz", nargs="?", default=os.path.join(ROOT, "data", "landmarks.npz"))
    ap.add_argument("--out", default=os.path.join(ROOT, "eval", "results.json"))
    args = ap.parse_args()

    X, y, signers, classes, meta = load(args.npz)
    n_classes = len(classes)
    print(f"{len(X)} samples, {n_classes} classes, signers {sorted(set(signers))}")

    results = {
        "dataset": {
            "name": "Surrey ASL Fingerspelling (Pugeault & Bowden, 2011)",
            "url": "https://www.cvssp.org/FingerSpellingKinect2011/",
            "images_in_dataset": meta["n_images_total"],
            "hands_detected_by_mediapipe": meta["n_detected"],
            "detection_rate": round(meta["n_detected"] / meta["n_images_total"], 4),
            "classes": classes,
            "n_classes": n_classes,
            "signers": sorted(set(signers)),
            "samples_per_signer": {s: int((signers == s).sum()) for s in sorted(set(signers))},
        },
        "training": {"epochs": EPOCHS, "seed": SEED, "features": "21 MediaPipe landmarks, wrist-centred, rotation-aligned, scale-normalized (63 dims)"},
    }

    # ---- Protocol 1: random stratified split (the leaky number) ----
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(sss.split(X, y))
    print(f"\n[random split] train {len(tr)} / test {len(te)}", flush=True)
    m = train(X[tr], y[tr], n_classes, verbose=True)
    pred = predict(m, X[te])
    rand_acc = float((pred == y[te]).mean())
    print(f"[random split] accuracy {rand_acc:.4f}")
    results["random_split"] = {
        "protocol": "stratified 80/20 over all samples, ignoring signer",
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "accuracy": round(rand_acc, 4),
        "warning": "near-duplicate frames from the same recording session appear on both sides of this split; this number overstates performance on a new person",
    }

    # ---- Protocol 2: leave-one-signer-out (the honest number) ----
    folds = []
    all_true, all_pred = [], []
    for s in sorted(set(signers)):
        te_m = signers == s
        tr_m = ~te_m
        print(f"\n[signer fold {s}] train {tr_m.sum()} / test {te_m.sum()}", flush=True)
        m = train(X[tr_m], y[tr_m], n_classes)
        pred = predict(m, X[te_m])
        acc = float((pred == y[te_m]).mean())
        print(f"[signer fold {s}] accuracy {acc:.4f}", flush=True)
        folds.append(
            {
                "held_out_signer": s,
                "n_train": int(tr_m.sum()),
                "n_test": int(te_m.sum()),
                "accuracy": round(acc, 4),
            }
        )
        all_true.append(y[te_m])
        all_pred.append(pred)

    all_true = np.concatenate(all_true)
    all_pred = np.concatenate(all_pred)
    accs = [f["accuracy"] for f in folds]
    cm = confusion(all_true, all_pred, n_classes)

    results["signer_independent"] = {
        "protocol": "leave-one-signer-out, 5 folds; no frame of the test person appears in training",
        "mean_accuracy": round(float(np.mean(accs)), 4),
        "std_accuracy": round(float(np.std(accs)), 4),
        "min_accuracy": round(float(np.min(accs)), 4),
        "max_accuracy": round(float(np.max(accs)), 4),
        "pooled_accuracy": round(float((all_pred == all_true).mean()), 4),
        "n_test_total": int(len(all_true)),
        "folds": folds,
        "per_class_accuracy": {
            classes[c]: (None if v is None else round(v, 4))
            for c, v in per_class_accuracy(all_true, all_pred, n_classes).items()
        },
        "confusion_matrix": cm.tolist(),
        "top_confusions": top_confusions(cm, classes),
    }
    results["leak_gap"] = round(rand_acc - float(np.mean(accs)), 4)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nrandom split      {rand_acc:.4f}")
    print(f"signer-independent {np.mean(accs):.4f} (range {np.min(accs):.4f}-{np.max(accs):.4f})")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
