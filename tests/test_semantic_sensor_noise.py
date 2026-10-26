#!/usr/bin/env python3
"""
Tests for the semantic sensor's noise model.

``DroneSemanticSensor._std_dev_noise`` is the standard deviation of the noise
added to the measured distance, so the noise must be zero-mean with that spread:
``np.random.normal(0, std_dev)``.  Passing the deviation as the first positional
argument instead makes ``loc`` equal to it, which offsets every measurement by a
constant and leaves a spread of 1 pixel.
"""
import inspect
import math

import numpy as np
import pytest

from swarm_rescue.simulation.ray_sensors.drone_semantic_sensor import (
    DroneSemanticSensor,
)
from swarm_rescue.simulation.utils.utils_noise import GaussianNoise


def _sample_semantic_noise(distance=100.0, samples=200_000):
    """Noise the sensor applied, measured through its production method."""
    noise = []
    for _ in range(samples):
        data = DroneSemanticSensor.Data(
            distance=distance, angle=0.0, entity_type=None, grasped=False,
        )
        sensor = object.__new__(DroneSemanticSensor)
        sensor._std_dev_noise = 2.5
        sensor._values = [data]
        DroneSemanticSensor._apply_noise(sensor)
        noise.append(sensor._values[0].distance - distance)
    return np.array(noise)


def test_semantic_noise_is_zero_mean():
    noise = _sample_semantic_noise()

    assert abs(noise.mean()) < 0.05, (
        f"semantic distance noise is offset by {noise.mean():.3f} px; "
        "it must be zero-mean"
    )


def test_semantic_noise_has_the_declared_spread():
    noise = _sample_semantic_noise()

    assert noise.std() == pytest.approx(2.5, abs=0.05), (
        f"noise spread is {noise.std():.3f} px, expected 2.5 px"
    )


def test_semantic_noise_spread_matches_lidar_noise():
    """Both range sensors must share the same 2.5 px model."""
    semantic = _sample_semantic_noise(samples=50_000)

    lidar_model = GaussianNoise(mean_noise=0, std_dev_noise=2.5)
    lidar = np.array([lidar_model.add_noise(0.0) for _ in range(50_000)])

    assert abs(semantic.mean() - lidar.mean()) < 0.1
    assert semantic.std() == pytest.approx(lidar.std(), abs=0.1)


def test_semantic_noise_call_shape_is_mean_and_scale():
    """The production call passes the deviation as the scale, not as loc."""
    source = inspect.getsource(DroneSemanticSensor._apply_noise)

    assert "np.random.normal(" in source
    assert "np.random.normal(self._std_dev_noise)" not in source, (
        "a single positional argument is `loc`, not the standard deviation"
    )


def test_semantic_noise_clamps_at_zero_without_biasing_other_readings():
    """The clamp at 0 must not leak a positive offset into normal readings."""
    noise = _sample_semantic_noise(distance=200.0, samples=50_000)

    assert noise.min() > -50
    assert abs(noise.mean()) < 0.1
