#!/usr/bin/env python3
"""
Tests for the round's disposal accounting.

A bomb disposed while several drones grasp it splits one unit of reward across
them (``DisposalCenter.activate`` grants ``entity.reward / grasped_by_size``), so
the round's progress must not be counted from float rewards: ten bombs held by
ten drones sum to 9.999999999999998, and the completion gate -- an exact
equality in ``GuiSR._update_disposal_progress`` and a ``>=`` in
``ScoreManager.compute_score`` -- would never fire, zeroing the time score of a
perfectly cleared round.

The round counts disposed bombs from the map's bomb state instead, which is
exact whatever the reward splits into.
"""
import math
from types import SimpleNamespace

import pytest

from swarm_rescue.simulation.gui_map.gui_sr import GuiSR
from swarm_rescue.simulation.reporting.score_manager import ScoreManager


class _Bomb:
    def __init__(self):
        self.disposed = False


def _gui(bomb_count=10, timestep=0):
    bombs = [_Bomb() for _ in range(bomb_count)]
    return SimpleNamespace(
        _the_map=SimpleNamespace(bombs=bombs),
        _disposed_number=0,
        _total_number_bombs=bomb_count,
        _full_disposal_timestep=0,
        _elapsed_timestep=timestep,
        _terminate=False,
    ), bombs


def _dispose_and_record(gui, *bombs):
    """Mark bombs disposed, then let the round record its progress."""
    for bomb in bombs:
        bomb.disposed = True
    GuiSR._update_disposal_progress(gui, GuiSR._disposed_bomb_count(gui))


def _step_rewards(total_bombs: int, drones_per_bomb: int):
    """Per-step reward totals, following the production path."""
    steps = []
    for _ in range(total_bombs):
        rewards = {}
        for drone_index in range(drones_per_bomb):
            # verbatim from DisposalCenter.activate
            rewards[drone_index] = (
                rewards.get(drone_index, 0.0) + 1 / drones_per_bomb
            )
        steps.append(float(sum(rewards.values())))
    return steps


# ---------------------------------------------------------------------------
# The float arithmetic the accounting must be immune to.
# ---------------------------------------------------------------------------
def test_split_reward_totals_are_inexact():
    """Pin the float behaviour that makes reward-based counting unsafe."""
    steps = _step_rewards(10, 10)

    assert all(step == 0.9999999999999999 for step in steps)
    assert math.fsum(steps) == 9.999999999999998
    assert math.fsum(steps) != 10.0
    assert math.fsum([1 / 10] * 100) == 10.0


# ---------------------------------------------------------------------------
# Counting comes from the map's bomb state.
# ---------------------------------------------------------------------------
def test_disposed_bomb_count_is_zero_before_any_disposal():
    gui, _ = _gui()
    assert GuiSR._disposed_bomb_count(gui) == 0


def test_disposed_bomb_count_tracks_the_map():
    gui, bombs = _gui(4)

    bombs[0].disposed = True
    bombs[2].disposed = True

    assert GuiSR._disposed_bomb_count(gui) == 2


# ---------------------------------------------------------------------------
# Completion is exact, whatever the reward split.
# ---------------------------------------------------------------------------
def test_completion_fires_on_the_last_bomb():
    gui, bombs = _gui(10, timestep=500)

    for bomb in bombs[:-1]:
        _dispose_and_record(gui, bomb)

    assert gui._disposed_number == 9
    assert gui._terminate is False

    _dispose_and_record(gui, bombs[-1])

    assert gui._disposed_number == 10
    assert gui._terminate is True
    assert gui._full_disposal_timestep == 500


@pytest.mark.parametrize("drones_per_bomb", [1, 2, 3, 7, 10])
def test_completion_is_independent_of_grasping_drone_count(drones_per_bomb):
    """The reward split changes, the count does not."""
    gui, bombs = _gui(10, timestep=200)

    # The split rewards are irrelevant to the count; this pins that the round
    # never consults them.
    for step_reward, bomb in zip(_step_rewards(10, drones_per_bomb), bombs):
        _dispose_and_record(gui, bomb)
        assert isinstance(step_reward, float)

    assert gui._disposed_number == 10
    assert gui._terminate is True
    assert gui._full_disposal_timestep == 200


def test_progress_is_recorded_once_per_step_not_per_bomb():
    """Several bombs disposed in one step complete the round in that step."""
    gui, bombs = _gui(5, timestep=42)

    for bomb in bombs:
        bomb.disposed = True
    GuiSR._update_disposal_progress(gui, GuiSR._disposed_bomb_count(gui))

    assert gui._disposed_number == 5
    assert gui._terminate is True
    assert gui._full_disposal_timestep == 42


def test_progress_never_moves_backwards():
    gui, bombs = _gui(10, timestep=90)
    _dispose_and_record(gui, bombs[0], bombs[1])
    assert gui._disposed_number == 2

    GuiSR._update_disposal_progress(gui, 0)

    assert gui._disposed_number == 2
    assert gui._terminate is False


def test_progress_never_exceeds_the_round_total():
    gui, bombs = _gui(10, timestep=50)

    GuiSR._update_disposal_progress(gui, 25)

    assert gui._disposed_number == 10
    assert gui._terminate is True


def test_completion_timestep_is_recorded_only_once():
    gui, bombs = _gui(2, timestep=10)
    _dispose_and_record(gui, bombs[0], bombs[1])
    assert gui._full_disposal_timestep == 10

    gui._elapsed_timestep = 99
    GuiSR._update_disposal_progress(gui, GuiSR._disposed_bomb_count(gui))

    assert gui._full_disposal_timestep == 10


def test_round_without_bombs_never_completes_early():
    gui, _ = _gui(0, timestep=1)

    GuiSR._update_disposal_progress(gui, GuiSR._disposed_bomb_count(gui))

    assert gui._disposed_number == 0
    assert gui._terminate is False


# ---------------------------------------------------------------------------
# The round must not read progress from rewards any more.
# ---------------------------------------------------------------------------
def test_on_update_does_not_count_rewards_as_disposals():
    import inspect

    source = inspect.getsource(GuiSR.on_update)

    assert "_update_disposal_progress(self._rewards_total(" not in source
    assert "_disposed_bomb_count" in source


# ---------------------------------------------------------------------------
# Scoring consequence: a cleared round reaches the full time score.
# ---------------------------------------------------------------------------
def test_score_manager_gives_time_score_to_a_fully_cleared_round():
    manager = ScoreManager(
        number_drones=10,
        max_timestep_limit=1000,
        max_walltime_limit=600,
        total_number_bombs=10,
    )

    gui, bombs = _gui(10, timestep=300)
    for bomb in bombs:
        _dispose_and_record(gui, bomb)

    assert gui._disposed_number == 10

    score, percent_disposed, score_timestep = manager.compute_score(
        gui._disposed_number,
        score_exploration=100.0,
        score_health_returned=100.0,
        elapsed_timestep=300,
        has_crashed=False,
    )

    assert percent_disposed == 100.0
    assert score_timestep > 0.0
    assert score > 0.0
