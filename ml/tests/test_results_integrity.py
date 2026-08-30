"""eval/results.json must reconcile with itself.

The accuracy figure is quoted in the README, in profile/master.yaml, on the live
page, in the social card and in the generated evaluation document. Every one of
those reads this file, so if the file is internally inconsistent the whole story
is wrong everywhere at once and nothing else in the suite would notice.

These tests recompute the published summaries from the raw confusion matrix. They
are deliberately not "does the number look plausible" -- they are "does the number
follow from the counts".
"""

import json
import os

import numpy as np
import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RESULTS = os.path.join(ROOT, "eval", "results.json")


@pytest.fixture(scope="module")
def results():
    if not os.path.exists(RESULTS):
        pytest.skip("eval/results.json missing -- run ml/evaluate.py")
    with open(RESULTS) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def cm(results):
    return np.array(results["signer_independent"]["confusion_matrix"], dtype=np.int64)


def test_matrix_is_square_and_matches_the_class_list(results, cm):
    n = results["dataset"]["n_classes"]
    assert n == len(results["dataset"]["classes"])
    assert cm.shape == (n, n)


def test_every_sample_is_accounted_for_exactly_once(results, cm):
    """Leave-one-signer-out holds out each sample exactly once, so the matrix
    must contain the whole detected dataset -- no more, no less."""
    si = results["signer_independent"]
    assert cm.sum() == si["n_test_total"]
    assert cm.sum() == results["dataset"]["hands_detected_by_mediapipe"]
    assert sum(f["n_test"] for f in si["folds"]) == si["n_test_total"]


def test_pooled_accuracy_is_the_matrix_diagonal(results, cm):
    pooled = cm.trace() / cm.sum()
    assert pooled == pytest.approx(results["signer_independent"]["pooled_accuracy"], abs=5e-5)


def test_mean_accuracy_is_the_mean_of_the_folds(results):
    si = results["signer_independent"]
    accs = [f["accuracy"] for f in si["folds"]]
    assert np.mean(accs) == pytest.approx(si["mean_accuracy"], abs=5e-5)
    assert np.std(accs) == pytest.approx(si["std_accuracy"], abs=5e-5)
    assert min(accs) == pytest.approx(si["min_accuracy"], abs=1e-9)
    assert max(accs) == pytest.approx(si["max_accuracy"], abs=1e-9)


def test_the_headline_is_the_mean_of_folds_not_the_pooled_figure(results):
    """These two differ whenever the folds are unequal in size. The page, the
    README and the resume bullet all quote the mean of folds, so the file must
    keep them as separate fields rather than letting one drift into the other."""
    si = results["signer_independent"]
    assert "mean_accuracy" in si and "pooled_accuracy" in si
    assert abs(si["mean_accuracy"] - si["pooled_accuracy"]) < 0.02


def test_per_class_accuracy_is_the_matrix_rows(results, cm):
    classes = results["dataset"]["classes"]
    published = results["signer_independent"]["per_class_accuracy"]
    for i, name in enumerate(classes):
        row = cm[i].sum()
        expected = cm[i, i] / row if row else None
        if expected is None:
            assert published[name] is None
        else:
            assert published[name] == pytest.approx(expected, abs=5e-5), name


def test_top_confusions_are_the_largest_off_diagonal_cells(results, cm):
    classes = results["dataset"]["classes"]
    published = results["signer_independent"]["top_confusions"]

    every = []
    for i in range(len(classes)):
        row = cm[i].sum()
        for j in range(len(classes)):
            if i != j and cm[i, j] > 0:
                every.append((int(cm[i, j]), classes[i], classes[j], cm[i, j] / row))
    every.sort(key=lambda t: -t[0])

    assert len(published) <= len(every)
    for got, want in zip(published, every[: len(published)]):
        assert got["count"] == want[0]
        assert got["true"] == want[1]
        assert got["predicted"] == want[2]
        assert got["rate"] == pytest.approx(want[3], abs=5e-5)

    # And they really are the largest: nothing left out beats the last one kept.
    if len(published) < len(every):
        assert every[len(published)][0] <= published[-1]["count"]


def test_the_leak_gap_is_the_difference_between_the_two_protocols(results):
    gap = results["random_split"]["accuracy"] - results["signer_independent"]["mean_accuracy"]
    assert results["leak_gap"] == pytest.approx(gap, abs=5e-5)
    assert results["leak_gap"] > 0, "the random split must be the flattering one, or the story is backwards"


def test_the_detection_rate_is_what_it_claims(results):
    d = results["dataset"]
    assert d["detection_rate"] == pytest.approx(
        d["hands_detected_by_mediapipe"] / d["images_in_dataset"], abs=5e-5
    )
    assert d["hands_detected_by_mediapipe"] <= d["images_in_dataset"]


def test_no_letter_is_defined_by_movement(results):
    """J and Z cannot be classified from a single frame. If either ever appears
    in the class list, something has gone wrong upstream in the dataset scan."""
    classes = {c.lower() for c in results["dataset"]["classes"]}
    assert "j" not in classes and "z" not in classes
    assert len(classes) == 24


def test_folds_cover_every_signer_once(results):
    si = results["signer_independent"]
    held_out = [f["held_out_signer"] for f in si["folds"]]
    assert sorted(held_out) == sorted(results["dataset"]["signers"])
    assert len(set(held_out)) == len(held_out)


def test_each_fold_trains_on_everyone_else(results):
    si = results["signer_independent"]
    per_signer = results["dataset"]["samples_per_signer"]
    for fold in si["folds"]:
        s = fold["held_out_signer"]
        assert fold["n_test"] == per_signer[s]
        assert fold["n_train"] == si["n_test_total"] - per_signer[s]
