"""Was the model configuration chosen, or just picked?

Two hidden layers of 256 and 128 with 0.3 dropout was written down on the first
attempt and never revisited. Sweeping configurations against the held-out signer
would answer the question by cheating: every number this project publishes would
then have been tuned on the thing it is measured against.

Nested cross-validation is the honest version. For each outer fold, one signer is
set aside untouched; the remaining four are themselves split leave-one-out to
choose a configuration; only then is the winner trained on all four and scored on
the signer nobody looked at. No test signer informs any choice at any point.

The question is not "can the number go up". It is whether the configuration
already shipping is the one an honest selection procedure would have chosen.

Usage:  python ml/measure_nested_selection.py
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import SEED, predict, train

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

CANDIDATES = {
    "shipped 256-128 d0.3": {"hidden": (256, 128), "dropout": 0.3},
    "smaller 128-64 d0.3": {"hidden": (128, 64), "dropout": 0.3},
    "larger 512-256 d0.3": {"hidden": (512, 256), "dropout": 0.3},
    "regularised 256-128 d0.5": {"hidden": (256, 128), "dropout": 0.5},
}


def score(X, y, n_classes, train_mask, test_mask, config):
    model = train(X[train_mask], y[train_mask], n_classes, **config)
    return float((predict(model, X[test_mask]) == y[test_mask]).mean())


def main():
    X, y, signers, classes, _ = load(os.path.join(ROOT, "data", "landmarks.npz"))
    n_classes = len(classes)
    all_signers = sorted(set(signers))

    outer = []
    for held_out in all_signers:
        outer_test = signers == held_out
        inner_pool = [s for s in all_signers if s != held_out]

        # --- inner: choose a configuration using only the four training signers
        inner_scores = {name: [] for name in CANDIDATES}
        for validation in inner_pool:
            va = signers == validation
            tr = ~va & ~outer_test
            for name, config in CANDIDATES.items():
                acc = score(X, y, n_classes, tr, va, config)
                inner_scores[name].append(acc)
                print(f"  [outer {held_out}] inner {validation} · {name}: {acc:.4f}", flush=True)

        means = {name: float(np.mean(v)) for name, v in inner_scores.items()}
        chosen = max(means, key=means.get)

        # --- outer: train the winner on all four, score on the untouched signer
        final = score(X, y, n_classes, ~outer_test, outer_test, CANDIDATES[chosen])
        print(f"[outer {held_out}] chose {chosen!r} -> {final:.4f}\n", flush=True)

        outer.append(
            {
                "held_out_signer": held_out,
                "inner_mean_accuracy": {k: round(v, 4) for k, v in means.items()},
                "chosen": chosen,
                "outer_accuracy": round(final, 4),
            }
        )

    nested_mean = float(np.mean([f["outer_accuracy"] for f in outer]))
    picks = [f["chosen"] for f in outer]
    results = {
        "protocol": "nested leave-one-signer-out; the outer signer informs no choice",
        "seed": SEED,
        "candidates": {k: {"hidden": list(v["hidden"]), "dropout": v["dropout"]} for k, v in CANDIDATES.items()},
        "outer_folds": outer,
        "nested_mean_accuracy": round(nested_mean, 4),
        "configurations_chosen": {name: picks.count(name) for name in CANDIDATES},
        "shipped_was_chosen_in_folds": picks.count("shipped 256-128 d0.3"),
    }

    published = os.path.join(ROOT, "eval", "results.json")
    if os.path.exists(published):
        with open(published) as f:
            results["published_mean_accuracy"] = json.load(f)["signer_independent"]["mean_accuracy"]
        results["difference_points"] = round(
            (nested_mean - results["published_mean_accuracy"]) * 100, 2
        )

    out = os.path.join(ROOT, "eval", "nested-selection.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"nested mean {nested_mean:.4f}")
    print(f"chosen per fold: {picks}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
