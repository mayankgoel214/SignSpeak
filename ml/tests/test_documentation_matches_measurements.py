"""Every figure quoted in prose must match the file it came from.

The live page renders its numbers from eval/*.json, so it cannot claim an
accuracy the repository did not measure. The README and the resume bullet have no
such protection: they are typed, and typed numbers drift the moment anything is
re-run. This project has already shipped a README that contradicted its own
repository once -- claiming a fixture was not committed while it was -- so the
prose is checked against the measurements rather than trusted.
"""

import json
import os
import re

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def _load(name):
    path = os.path.join(ROOT, "eval", name)
    if not os.path.exists(path):
        pytest.skip(f"eval/{name} missing")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def readme():
    with open(os.path.join(ROOT, "README.md")) as f:
        return f.read()


@pytest.fixture(scope="module")
def results():
    return _load("results.json")


def quoted(text, pattern):
    """Every number matching a pattern, so a figure appearing twice must be
    right in both places."""
    return [float(m) for m in re.findall(pattern, text)]


def test_the_headline_accuracy_is_the_measured_one(readme, results):
    mean = results["signer_independent"]["mean_accuracy"] * 100
    found = quoted(readme, r"\*\*(\d{2}\.\d)% on a signer")
    assert found, "the README no longer states the headline figure"
    for value in found:
        assert value == pytest.approx(mean, abs=0.05)


def test_the_random_split_figure_is_the_measured_one(readme, results):
    random = results["random_split"]["accuracy"] * 100
    found = quoted(readme, r"scores \*\*(\d{2}\.\d)%\*\* on a random")
    assert found
    for value in found:
        assert value == pytest.approx(random, abs=0.05)


def test_the_gap_is_the_difference_between_them(readme, results):
    gap = results["leak_gap"] * 100
    found = quoted(readme, r"The (\d\.\d)-point gap")
    assert found
    for value in found:
        assert value == pytest.approx(gap, abs=0.05)


def test_the_sample_count_is_the_measured_one(readme, results):
    n = results["signer_independent"]["n_test_total"]
    assert f"{n:,}" in readme, f"the README should quote {n:,} samples"


def test_the_per_fold_range_is_the_measured_one(readme, results):
    si = results["signer_independent"]
    lo, hi = si["min_accuracy"] * 100, si["max_accuracy"] * 100
    assert re.search(rf"{lo:.1f}% to {hi:.1f}%", readme), "per-fold range does not match"


def test_the_class_count_matches(readme, results):
    assert f"{results['dataset']['n_classes']} letters" in readme


def test_the_detection_rate_matches(readme, results):
    missed = (1 - results["dataset"]["detection_rate"]) * 100
    found = quoted(readme, r"(\d\.\d\d)% of dataset images produce no hand detection")
    assert found
    assert found[0] == pytest.approx(missed, abs=0.01)


def test_the_leakage_figures_match(readme):
    leak = _load("leakage.json")
    rs, si = leak["random_split"], leak["signer_independent"]["pooled"]
    assert f"**{rs['median']:.2f}**" in readme, "random-split median distance not quoted correctly"
    assert f"**{si['median']:.2f}**" in readme, "signer-split median distance not quoted correctly"
    found = quoted(readme, r"\*\*(\d\.\d)%\*\* land within 0.05")
    assert found
    assert found[0] == pytest.approx(rs["share_within_0.05"] * 100, abs=0.1)


def test_the_calibration_direction_and_size_match(readme):
    cal = _load("calibration.json")
    gap = abs(cal["overconfidence"]) * 100
    direction = "under" if cal["overconfidence"] < 0 else "over"
    assert f"**{direction}**-confident by {gap:.1f}" in readme, (
        f"the README should say {direction}-confident by {gap:.1f} points"
    )


def test_the_generated_evaluation_document_is_current():
    """docs/EVALUATION.md is generated. If it has drifted from results.json the
    generator was not re-run, and the document is quoting an older experiment."""
    doc_path = os.path.join(ROOT, "docs", "EVALUATION.md")
    if not os.path.exists(doc_path):
        pytest.skip("docs/EVALUATION.md missing")
    with open(doc_path) as f:
        doc = f.read()
    results = _load("results.json")
    si = results["signer_independent"]
    assert f"**{si['mean_accuracy']:.1%} accuracy" in doc
    assert f"{si['n_test_total']:,}" in doc
    for fold in si["folds"]:
        assert f"{fold['accuracy']:.2%}" in doc, f"fold {fold['held_out_signer']} missing from the document"
