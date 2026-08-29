"""The feature transform is the model's entire defence against a new person's
hand being a different size, in a different place, at a different angle. These
tests assert that defence actually holds, rather than assuming it."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from features import FEATURE_DIM, normalize


@pytest.fixture
def hand():
    rng = np.random.default_rng(7)
    return rng.normal(size=(21, 3)) * 0.1 + np.array([0.5, 0.5, 0.0])


def test_shape_and_dtype(hand):
    f = normalize(hand)
    assert f.shape == (FEATURE_DIM,)
    assert f.dtype == np.float32


def test_wrist_is_the_origin(hand):
    assert np.allclose(normalize(hand)[:3], 0, atol=1e-6)


def test_translation_invariant(hand):
    moved = hand + np.array([0.3, -0.2, 0.05])
    assert np.allclose(normalize(hand), normalize(moved), atol=1e-5)


def test_scale_invariant(hand):
    assert np.allclose(normalize(hand), normalize(hand * 2.5), atol=1e-5)


def test_in_plane_rotation_invariant(hand):
    theta = 0.7
    c, s = np.cos(theta), np.sin(theta)
    rot = hand.copy()
    rot[:, 0] = c * hand[:, 0] - s * hand[:, 1]
    rot[:, 1] = s * hand[:, 0] + c * hand[:, 1]
    assert np.allclose(normalize(hand), normalize(rot), atol=1e-5)


def test_left_hand_maps_onto_the_right_hand_manifold(hand):
    mirrored = hand.copy()
    mirrored[:, 0] = -mirrored[:, 0]
    assert np.allclose(normalize(hand, "Right"), normalize(mirrored, "Left"), atol=1e-6)


def test_degenerate_hand_does_not_divide_by_zero():
    f = normalize(np.zeros((21, 3)))
    assert np.all(np.isfinite(f))


def test_farthest_landmark_is_at_unit_distance(hand):
    pts = normalize(hand).reshape(21, 3)
    assert np.isclose(np.max(np.linalg.norm(pts, axis=1)), 1.0, atol=1e-5)
