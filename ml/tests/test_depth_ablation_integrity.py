"""The depth ablation exists to answer "why is z in the feature vector".

Its value is entirely in being a fair comparison: same protocol, same seed, same
training code, one variable changed. These tests check that it was.
"""

import json
import os

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PATH = os.path.join(ROOT, "eval", "depth-ablation.json")


@pytest.fixture(scope="module")
def ablation():
    if not os.path.exists(PATH):
        pytest.skip("eval/depth-ablation.json missing -- run ml/measure_depth_ablation.py")
    with open(PATH) as f:
        return json.load(f)


def test_only_the_feature_width_differs(ablation):
    assert ablation["arms"]["xyz"]["dims"] == 63
    assert ablation["arms"]["xy_only"]["dims"] == 42
    assert set(ablation["arms"]["xyz"]["per_fold"]) == set(ablation["arms"]["xy_only"]["per_fold"])


def test_the_control_arm_reproduces_the_real_evaluation(ablation):
    """The xyz arm is the shipped configuration. If it does not land on the
    published per-fold numbers, the ablation is not comparing what it claims."""
    results_path = os.path.join(ROOT, "eval", "results.json")
    if not os.path.exists(results_path):
        pytest.skip("eval/results.json missing")
    with open(results_path) as f:
        folds = {f["held_out_signer"]: f["accuracy"] for f in json.load(f)["signer_independent"]["folds"]}
    for signer, accuracy in ablation["arms"]["xyz"]["per_fold"].items():
        assert accuracy == pytest.approx(folds[signer], abs=1e-4), signer


def test_the_difference_matches_the_two_arms(ablation):
    a = ablation["arms"]["xyz"]["mean"]
    b = ablation["arms"]["xy_only"]["mean"]
    assert ablation["difference_points"] == pytest.approx((a - b) * 100, abs=0.01)


def test_the_verdict_is_the_one_the_numbers_support(ablation):
    """A conclusion drifting away from its own evidence is the specific failure
    this project keeps finding, so it is asserted rather than trusted."""
    gap = ablation["difference_points"] / 100
    verdict = ablation["verdict"]
    if gap > 0.002:
        assert verdict == "z earns its place"
    elif abs(gap) <= 0.002:
        assert verdict == "dropping z is no worse"
    else:
        assert verdict == "z is costing accuracy"


def test_the_difference_is_smaller_than_the_fold_spread(ablation):
    """The whole reading of this experiment is 'that is noise'. If the gap ever
    exceeds the spread between folds, that reading is no longer honest and the
    generated document says something it should not."""
    results_path = os.path.join(ROOT, "eval", "results.json")
    if not os.path.exists(results_path):
        pytest.skip("eval/results.json missing")
    with open(results_path) as f:
        si = json.load(f)["signer_independent"]
    spread = (si["max_accuracy"] - si["min_accuracy"]) * 100
    assert abs(ablation["difference_points"]) < spread
