"""Things the repository must not contain.

The Surrey dataset is licensed for research use and is not mine to redistribute.
A fixture of 240 cropped hand photographs is easy to generate and easy to commit
by accident -- it was, in the first commit of the rebuild, while the README, the
generator and the test file all said it had not been. Three claims and the tree
disagreed, and nothing failed.
"""

import json
import os
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
IMAGE_FIXTURE = "tests/fixtures/browser-cases.json"


def tracked():
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.split()


@pytest.fixture(scope="module")
def files():
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        pytest.skip("not a git checkout")
    return tracked()


def test_the_image_fixture_is_not_tracked(files):
    assert IMAGE_FIXTURE not in files, (
        f"{IMAGE_FIXTURE} contains dataset photographs and must not be committed; "
        "regenerate it locally with ml/make_browser_fixture.py"
    )


def test_the_image_fixture_is_ignored():
    with open(os.path.join(ROOT, ".gitignore")) as f:
        assert IMAGE_FIXTURE in f.read().split()


def test_no_tracked_fixture_carries_encoded_images(files):
    for path in files:
        if not path.startswith("tests/fixtures/"):
            continue
        with open(os.path.join(ROOT, path)) as f:
            payload = json.load(f)
        for case in payload.get("cases", []):
            assert "png_base64" not in case, f"{path} carries dataset images"


def test_the_committed_fixture_is_landmarks_and_is_usable(files):
    path = "tests/fixtures/landmark-cases.json"
    assert path in files, "the landmark fixture must be committed, or CI loses parity coverage"
    with open(os.path.join(ROOT, path)) as f:
        cases = json.load(f)["cases"]
    assert len(cases) >= 24
    for case in cases:
        assert len(case["python_landmarks"]) == 21
        assert all(len(p) == 3 for p in case["python_landmarks"])
        assert case["letter"] and case["python_prediction"] and case["signer"]
