"""eval/calibration.json must reconcile with itself, like results.json does.

The page renders a claim about how much to trust the number beside a letter. If
the file behind it is inconsistent, that claim is wrong in a way no reader could
detect, and reassuring miscalibration is worse than none at all.
"""

import json
import os

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PATH = os.path.join(ROOT, "eval", "calibration.json")


@pytest.fixture(scope="module")
def cal():
    if not os.path.exists(PATH):
        pytest.skip("eval/calibration.json missing -- run ml/measure_calibration.py")
    with open(PATH) as f:
        return json.load(f)


def test_every_prediction_lands_in_exactly_one_band(cal):
    assert sum(b["n"] for b in cal["reliability"]) == cal["n_predictions"]
    assert sum(b["share"] for b in cal["reliability"]) == pytest.approx(1.0, abs=1e-3)


def test_band_shares_match_their_counts(cal):
    for band in cal["reliability"]:
        assert band["share"] == pytest.approx(band["n"] / cal["n_predictions"], abs=5e-4), band["bin"]


def test_the_gap_in_each_band_is_confidence_minus_accuracy(cal):
    for band in cal["reliability"]:
        assert band["gap"] == pytest.approx(band["mean_confidence"] - band["accuracy"], abs=1e-3), band["bin"]


def test_confidence_stays_inside_its_own_band(cal):
    for band in cal["reliability"]:
        lo, hi = (float(x) for x in band["bin"].replace("–", "-").split("-"))
        assert lo <= band["mean_confidence"] <= hi + 1e-9, band["bin"]


def test_expected_calibration_error_is_the_weighted_gap(cal):
    ece = sum(b["share"] * abs(b["gap"]) for b in cal["reliability"])
    assert cal["expected_calibration_error"] == pytest.approx(ece, abs=2e-3)


def test_overconfidence_is_mean_confidence_minus_accuracy(cal):
    assert cal["overconfidence"] == pytest.approx(
        cal["mean_confidence"] - cal["overall_accuracy"], abs=1e-3
    )


def test_raising_the_floor_keeps_fewer_frames_and_scores_better(cal):
    """Both must be monotonic. If they are not, the threshold table is telling a
    story the data does not support and the chosen floor cannot be defended."""
    rows = sorted(cal["thresholds"], key=lambda t: t["threshold"])
    kept = [r["frames_kept"] for r in rows]
    assert kept == sorted(kept, reverse=True)
    scored = [r["accuracy_of_kept"] for r in rows if r["accuracy_of_kept"] is not None]
    assert scored == sorted(scored)


def test_the_zero_threshold_is_the_headline_accuracy(cal):
    zero = next(t for t in cal["thresholds"] if t["threshold"] == 0.0)
    assert zero["frames_kept"] == pytest.approx(1.0, abs=1e-6)
    assert zero["accuracy_of_kept"] == pytest.approx(cal["overall_accuracy"], abs=1e-3)


def test_it_agrees_with_the_evaluation_it_shares_a_protocol_with(cal):
    """Same folds, same data, so the pooled accuracy must match results.json."""
    results_path = os.path.join(ROOT, "eval", "results.json")
    if not os.path.exists(results_path):
        pytest.skip("eval/results.json missing")
    with open(results_path) as f:
        results = json.load(f)
    si = results["signer_independent"]
    assert cal["n_predictions"] == si["n_test_total"]
    assert cal["overall_accuracy"] == pytest.approx(si["pooled_accuracy"], abs=1e-3)


def test_the_page_s_commit_floor_is_one_of_the_measured_thresholds(cal):
    """web/app.js commits at 0.7. It must appear here, or the page is using a
    setting nobody measured."""
    app = os.path.join(ROOT, "web", "app.js")
    with open(app) as f:
        source = f.read()
    line = next(l for l in source.splitlines() if "CONFIDENCE_FLOOR" in l and "=" in l)
    floor = float(line.split("=")[1].strip().rstrip(";"))
    assert any(abs(t["threshold"] - floor) < 1e-9 for t in cal["thresholds"]), (
        f"the page commits at {floor}, which measure_calibration.py never measured"
    )
