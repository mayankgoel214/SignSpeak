"""Measure the near-duplicate structure this whole evaluation is built on.

Two claims run through the README, the page and the resume bullet, and neither
had been measured:

  1. A random split leaks, because the dataset is continuous recordings and
     neighbouring frames are near-duplicates of one another.
  2. Leave-one-signer-out does not leak, because no frame of the test person is
     in training.

The first is the reason the 98.7% is thrown away. The second is the reason the
92.2% is kept. If either is false the conclusion is upside down, so this
quantifies both from the feature vectors themselves: for every held-out sample,
how far away is its nearest training neighbour, under each protocol.

It also looks for the failure that would quietly destroy the honest number --
the same recording session appearing under two signer labels, which would make
leave-one-signer-out leak like a random split while looking rigorous.

Usage:  python ml/measure_leakage.py
"""

import json
import os
import sys

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataset import load
from model import SEED

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# A distance in normalized feature units, where the whole hand spans 1. Two hands
# this close are the same pose to any useful precision -- for reference, the
# browser and Python disagree by about 0.03 on the same image.
NEAR = 0.05


def neighbour_distances(train, query):
    nn = NearestNeighbors(n_neighbors=1, algorithm="auto").fit(train)
    distances, _ = nn.kneighbors(query)
    return distances[:, 0]


def summarise(distances):
    return {
        "n": int(len(distances)),
        "median": round(float(np.median(distances)), 4),
        "p05": round(float(np.percentile(distances, 5)), 4),
        "p25": round(float(np.percentile(distances, 25)), 4),
        "share_within_0.05": round(float((distances < NEAR).mean()), 4),
        "share_within_0.02": round(float((distances < 0.02).mean()), 4),
    }


def main():
    X, y, signers, classes, _meta = load(os.path.join(ROOT, "data", "landmarks.npz"))
    print(f"{len(X)} samples, {len(set(signers))} signers", flush=True)

    results = {"near_threshold": NEAR}

    # --- exact duplicates, the crudest form of the problem ---
    _, first, counts = np.unique(
        np.round(X, 5), axis=0, return_index=True, return_counts=True
    )
    duplicated = int((counts > 1).sum())
    results["exact_duplicate_feature_vectors"] = {
        "distinct_vectors": int(len(counts)),
        "vectors_appearing_more_than_once": duplicated,
        "share_of_samples_in_a_duplicate_group": round(
            float(counts[counts > 1].sum() / len(X)), 4
        ),
    }
    print(f"exact duplicates: {duplicated} repeated vectors", flush=True)

    # --- protocol 1: a random split, the number that gets thrown away ---
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(sss.split(X, y))
    print("[random split] nearest training neighbour …", flush=True)
    results["random_split"] = summarise(neighbour_distances(X[tr], X[te]))

    # --- protocol 2: leave-one-signer-out, the number that is kept ---
    per_fold = {}
    pooled = []
    for s in sorted(set(signers)):
        te_mask = signers == s
        print(f"[fold {s}] nearest training neighbour …", flush=True)
        d = neighbour_distances(X[~te_mask], X[te_mask])
        per_fold[s] = summarise(d)
        pooled.append(d)
    results["signer_independent"] = {"pooled": summarise(np.concatenate(pooled)), "per_fold": per_fold}

    # --- the failure that would look rigorous and not be ---
    # If two signer labels cover the same recording session, leave-one-signer-out
    # is a random split wearing a disguise.
    cross = {}
    for a in sorted(set(signers)):
        for b in sorted(set(signers)):
            if a >= b:
                continue
            d = neighbour_distances(X[signers == a], X[signers == b])
            cross[f"{a}->{b}"] = {
                "median": round(float(np.median(d)), 4),
                "min": round(float(d.min()), 4),
                "share_within_0.05": round(float((d < NEAR).mean()), 4),
            }
    results["cross_signer"] = cross

    out = os.path.join(ROOT, "eval", "leakage.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    rs = results["random_split"]
    si = results["signer_independent"]["pooled"]
    print("\nnearest training neighbour, in normalized feature units")
    print(f"  random split        median {rs['median']:.4f}   within {NEAR}: {rs['share_within_0.05']:.1%}")
    print(f"  signer-independent  median {si['median']:.4f}   within {NEAR}: {si['share_within_0.05']:.1%}")
    print("\ncross-signer nearest neighbour (a high median means genuinely different people)")
    for pair, r in cross.items():
        print(f"  {pair}   median {r['median']:.4f}   within {NEAR}: {r['share_within_0.05']:.2%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
