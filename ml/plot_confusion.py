"""Render eval/results.json's leave-one-signer-out confusion matrix to a PNG."""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "eval", "results.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "eval", "confusion-matrix.png")
    with open(src) as f:
        r = json.load(f)

    classes = [c.upper() for c in r["dataset"]["classes"]]
    cm = np.array(r["signer_independent"]["confusion_matrix"], dtype=float)
    row = cm.sum(axis=1, keepdims=True)
    norm = np.divide(cm, row, out=np.zeros_like(cm), where=row > 0)

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(norm, cmap="magma", vmin=0, vmax=1)
    ax.set_xticks(range(len(classes)), classes, fontsize=8)
    ax.set_yticks(range(len(classes)), classes, fontsize=8)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true letter")
    mean = r["signer_independent"]["mean_accuracy"]
    ax.set_title(
        f"Leave-one-signer-out confusion, {len(classes)} ASL letters\n"
        f"mean accuracy {mean:.1%} over 5 held-out signers "
        f"({r['signer_independent']['n_test_total']:,} test samples)",
        fontsize=11,
    )
    fig.colorbar(im, ax=ax, fraction=0.046, label="share of true class")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
