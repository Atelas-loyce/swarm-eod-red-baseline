#!/usr/bin/env python3
"""
Tests for the collision damage cooldown.

Health loss must depend on the simulation, not on how fast the host runs it: the
same colliding steps must cost the same health whether the round is replayed at
30 steps/s or as fast as the CPU allows.  The cooldown is therefore expressed in
simulated time (timesteps), one damage tick per simulated second.
"""
from types import SimpleNamespace

import pytest

from swarm_rescue.simulation.drone.drone_abstract import DroneAbstract
from swarm_rescue.simulation.utils.constants import (
    COLLISION_COOLDOWN_SECONDS,
    FRAME_RATE,
)


class _CollisionDrone:
    """Just enough of DroneAbstract to run the real collision handlers."""

    collide_wall = DroneAbstract.collide_wall
    collide_drone = DroneAbstract.collide_drone
    _collision_damage_allowed = DroneAbstract._collision_damage_allowed
    _apply_collision_damage = DroneAbstract._apply_collision_damage

    def __init__(self):
        self.identifier = 0
        self._drone_health = 50
        self.removed = False
        self.elapsed_timestep = 0
        self._last_collision_damage_timestep = None
        self.grasper = SimpleNamespace(_release_grasping=lambda: None)
        self._playground = SimpleNamespace(remove=lambda *_a, **_k: None)


COOLDOWN_STEPS = int(round(COLLISION_COOLDOWN_SECONDS / FRAME_RATE))


def _run_collisions(drone, steps, handler="collide_wall"):
    """Advance the drone one timestep at a time, colliding on every step."""
    method = getattr(drone, handler)
    for _ in range(steps):
        drone.elapsed_timestep += 1
        method()


# ---------------------------------------------------------------------------
# Damage follows simulated time, not wall time.
# ---------------------------------------------------------------------------
def test_collisions_at_the_same_timestep_cost_the_same_health():
    """Two drones colliding on identical timesteps lose identical health."""
    fast, slow = _CollisionDrone(), _CollisionDrone()

    _run_collisions(fast, 90)
    _run_collisions(slow, 90)

    assert fast._drone_health == slow._drone_health


def test_repeated_collisions_in_one_timestep_cost_one_tick():
    """Several contacts inside a single timestep is still one collision event."""
    drone = _CollisionDrone()
    drone.elapsed_timestep = 10

    for _ in range(50):
        drone.collide_wall()

    assert drone._drone_health == 49


def test_cooldown_is_measured_in_simulated_seconds():
    drone = _CollisionDrone()
    drone.elapsed_timestep = 1

    drone.collide_wall()
    assert drone._drone_health == 49

    # Just before the cooldown expires: still the same damage tick.
    drone.elapsed_timestep = 1 + COOLDOWN_STEPS - 1
    drone.collide_wall()
    assert drone._drone_health == 49

    # The cooldown has elapsed in simulated time: a new damage tick.
    drone.elapsed_timestep = 1 + COOLDOWN_STEPS
    drone.collide_wall()
    assert drone._drone_health == 48


@pytest.mark.parametrize("steps", [0, 1, COOLDOWN_STEPS, COOLDOWN_STEPS + 1,
                                   4 * COOLDOWN_STEPS + 7])
def test_no_damage_twice_within_the_cooldown(steps):
    """Collision on step 1, then on `steps` later: exactly two ticks at most."""
    drone = _CollisionDrone()
    drone.elapsed_timestep = 1
    drone.collide_wall()

    drone.elapsed_timestep = 1 + steps
    drone.collide_wall()

    expected_second_tick = steps >= COOLDOWN_STEPS
    assert drone._drone_health == (48 if expected_second_tick else 49)


def test_drone_and_wall_collisions_share_one_cooldown():
    drone = _CollisionDrone()
    drone.elapsed_timestep = 5

    drone.collide_wall()
    drone.collide_drone()

    assert drone._drone_health == 49


def test_health_below_zero_removes_the_drone_once():
    removed_calls = []
    drone = _CollisionDrone()
    drone._playground = SimpleNamespace(remove=lambda *a, **k: removed_calls.append(a))

    drone._drone_health = 1
    drone.elapsed_timestep = 1
    drone.collide_wall()

    assert drone._drone_health == 0
    assert len(removed_calls) == 1

    # A later collision on a removed drone must not remove it again.
    drone.removed = True
    drone.elapsed_timestep = 1 + COOLDOWN_STEPS
    drone.collide_wall()
    assert len(removed_calls) == 1


def test_no_wall_clock_dependency_remains():
    """The cooldown must not read any real-time source."""
    import inspect

    source = inspect.getsource(DroneAbstract.collide_wall)
    assert "get_elapsed_time" not in source
    assert "perf_counter" not in source
    assert "time." not in source
