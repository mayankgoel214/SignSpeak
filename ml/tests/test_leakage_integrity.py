"""The leakage measurement is what turns two assertions into two facts.

The README, the page and the resume bullet all say a random split leaks and a
signer split does not. eval/leakage.json is the evidence. These tests check that
the evidence actually says what it is quoted as saying -- and, more importantly,
that the conclusion drawn from it is the one the numbers support.
"""

import json
import os

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PATH = os.path.join(ROOT, "eval", "leakage.json")


@pytest.fixture(scope="module")
def leak():
    if not os.path.exists(PATH):
        pytest.skip("eval/leakage.json missing -- run ml/measure_leakage.py")
    with open(PATH) as f:
        return json.load(f)


def test_the_random_split_really_does_leak(leak):
    """If held-out frames were not unusually close to training frames, the whole
    reason for discarding the 98.7% would evaporate."""
    rs = leak["random_split"]
    si = leak["signer_independent"]["pooled"]
    assert rs["median"] < si["median"], (
        "a random split must put held-out samples closer to training data than a "
        "signer split does, or the story about why it is discarded is wrong"
    )
    assert rs["share_within_0.05"] > si["share_within_0.05"]


def test_the_signer_split_really_does_not(leak):
    si = leak["signer_independent"]["pooled"]
    # Two MediaPipe builds disagree on the same photograph by about 0.03, so
    # anything inside 0.05 is the same hand by any useful definition.
    assert si["share_within_0.05"] < 0.005, (
        "held-out signers should have essentially no near-duplicates in training"
    )


def test_no_two_signers_are_the_same_recording_session(leak):
    """The failure that would look rigorous and not be: if one session were
    labelled as two people, leave-one-signer-out would leak like a random split
    while appearing careful."""
    for pair, r in leak["cross_signer"].items():
        assert r["share_within_0.05"] < 0.005, f"{pair} share near-duplicate hands"
        assert r["median"] > 0.15, f"{pair} are suspiciously similar overall"


def test_there_are_no_exact_duplicate_samples(leak):
    d = leak["exact_duplicate_feature_vectors"]
    assert d["vectors_appearing_more_than_once"] == 0
    assert d["share_of_samples_in_a_duplicate_group"] == 0


def test_every_fold_is_clean_not_just_the_average(leak):
    """A pooled figure can hide one bad fold, and one leaky fold is enough to
    inflate the mean everything else is quoted from."""
    for signer, r in leak["signer_independent"]["per_fold"].items():
        assert r["share_within_0.05"] < 0.01, f"fold {signer} has near-duplicates in training"


def test_the_percentiles_are_ordered(leak):
    for section in [leak["random_split"], leak["signer_independent"]["pooled"]]:
        assert section["p05"] <= section["p25"] <= section["median"]
        assert section["share_within_0.02"] <= section["share_within_0.05"]
