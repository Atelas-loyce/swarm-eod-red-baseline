"""Tests for the blue-team ScoreManager, focusing on the time score.

The blue time score is awarded only to a round that disposed every bomb: it
then uses the same curve as the red team (full at or before half the timestep
limit, 0 at the limit, linear in between). An incomplete round earns 0 however
it ended -- including a round that reached the walltime limit before the
timestep limit, which leaves ``elapsed_timestep`` below the limit.
"""

import pytest

from swarm_rescue.simulation.reporting.score_manager import ScoreManager


def _manager(max_timestep_limit: int = 2000,
             total_number_bombs: int = 5,
             time_best_ratio: float = 0.5,
             **kwargs) -> ScoreManager:
    return ScoreManager(
        number_drones=10,
        max_timestep_limit=max_timestep_limit,
        max_walltime_limit=90,
        total_number_bombs=total_number_bombs,
        time_best_ratio=time_best_ratio,
        **kwargs,
    )


@pytest.mark.parametrize("elapsed,expected", [
    (0, 100.0),          # instant all-disposal: full
    (500, 100.0),        # before half the limit: full
    (1000, 100.0),       # exactly half the limit: full
    (1250, 75.0),        # midpoint between best and limit
    (1500, 50.0),        # three quarters of the limit
    (2000, 0.0),         # at the limit: zero
    (3000, 0.0),         # past the limit: clamped to zero
])
def test_time_score_curve(elapsed, expected):
    """score_timestep out of 100 mirrors the red-team formula."""
    _, _, score_timestep = _manager().compute_score(
        5, 0.0, 0.0, elapsed
    )
    assert score_timestep == pytest.approx(expected)


def test_time_score_needs_full_disposal():
    """A round that leaves bombs behind earns no time score, whatever ended
    it: the timestep limit (elapsed = limit) or the walltime limit first
    (elapsed well below the limit, host speed dependent)."""
    for elapsed in (0, 500, 800, 1830, 1999, 2000):
        _, _, score_timestep = _manager().compute_score(3, 0.0, 0.0, elapsed)
        assert score_timestep == 0.0
    # The same elapsed timestep with full disposal does score on the curve.
    _, _, complete = _manager().compute_score(5, 0.0, 0.0, 1830)
    assert complete == pytest.approx(17.0)


def test_incomplete_round_keeps_only_the_other_components():
    """Only the time component is gated; disposal/health still score."""
    score, percentage_disposed, score_timestep = _manager().compute_score(
        3, 0.0, 50.0, 800
    )
    assert percentage_disposed == pytest.approx(60.0)
    assert score_timestep == 0.0
    # 0.6 * 60 (disposal) + 0.2 * 50 (health) + 0.2 * 0 (time) = 46
    assert score == pytest.approx(46.0)


def test_zero_bomb_map_counts_as_complete():
    manager = _manager(total_number_bombs=0)
    score, percentage_disposed, score_timestep = manager.compute_score(
        0, 0.0, 0.0, 1000
    )
    assert percentage_disposed == 100.0
    assert score_timestep == 100.0
    assert score == pytest.approx(0.6 * 100 + 0.2 * 100)


def test_time_score_contributes_to_total():
    manager = _manager()
    score, percentage_disposed, score_timestep = manager.compute_score(
        5, 0.0, 0.0, 1500
    )
    assert percentage_disposed == 100.0
    assert score_timestep == 50.0
    # 0.6 * 100 (disposal) + 0.2 * 0 (exploration) + 0.2 * 50 (time) = 70
    assert score == pytest.approx(70.0)


def test_crashed_round_earns_zero_time():
    """A crashed round gets no time score, mirroring the red team."""
    for elapsed in (0, 500, 1500):
        _, _, score_timestep = _manager().compute_score(
            5, 0.0, 0.0, elapsed, has_crashed=True
        )
        assert score_timestep == 0.0


def test_time_best_ratio_configurable():
    manager = _manager(time_best_ratio=0.25)
    _, _, score_timestep = manager.compute_score(5, 0.0, 0.0, 1000)
    # best = 0.25 * 2000 = 500; at elapsed 1000 -> (2000-1000)/(2000-500) = 2/3
    assert score_timestep == pytest.approx(100.0 * 2 / 3)
