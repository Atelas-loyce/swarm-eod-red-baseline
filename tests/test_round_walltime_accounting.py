#!/usr/bin/env python3
"""
Tests for the round's wall-clock accounting.

The round's elapsed wall time is what the round limit is judged against, so no
work that happens while closing the round -- computing health statistics,
noticing the state recorder, writing the compressed NPZ -- may fall outside it.
The round re-samples the clock after that work, which is also how a round that
overruns while saving is still reported as overrunning.
"""
from types import SimpleNamespace

import pytest

from swarm_rescue.simulation.gui_map.gui_sr import GuiSR


class _Clock:
    """A monotonically advancing clock the test controls explicitly."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _gui(clock, pre_save_elapsed=0.0, max_walltime=600, terminate=False):
    """A round that has run ``pre_save_elapsed`` seconds when it closes."""
    clock.now = 1000.0 + pre_save_elapsed
    return SimpleNamespace(
        _start_timestamp=1000.0,
        _elapsed_walltime=max(pre_save_elapsed, 0.001),
        _max_walltime_limit=max_walltime,
        _is_max_walltime_limit_reached=False,
        _terminate=terminate,
    )


# ---------------------------------------------------------------------------
# The tail of the round must be inside the measured wall time.
# ---------------------------------------------------------------------------
def test_walltime_sample_after_round_close_includes_the_save():
    clock = _Clock()
    gui = _gui(clock, pre_save_elapsed=120.0)

    # The round is being closed: this takes real time (health stats + NPZ).
    clock.advance(7.5)
    GuiSR._sample_walltime_after_round_close(gui, clock)

    assert gui._elapsed_walltime == pytest.approx(127.5)


def test_round_overrun_during_save_is_detected_after_the_save():
    """A round that finishes its save past the limit must report the overrun."""
    clock = _Clock()
    gui = _gui(clock, pre_save_elapsed=595.0, max_walltime=600)

    # The save pushes the round past its limit.
    clock.advance(10.0)
    GuiSR._sample_walltime_after_round_close(gui, clock)

    assert gui._elapsed_walltime == 600
    assert gui._is_max_walltime_limit_reached is True


def test_round_inside_the_limit_does_not_set_the_overrun_flag():
    clock = _Clock()
    gui = _gui(clock, pre_save_elapsed=100.0, max_walltime=600)

    clock.advance(1.0)
    GuiSR._sample_walltime_after_round_close(gui, clock)

    assert gui._elapsed_walltime == pytest.approx(101.0)
    assert gui._is_max_walltime_limit_reached is False


def test_walltime_sample_is_never_below_the_pre_save_value():
    """Closing the round cannot make the round look shorter."""
    clock = _Clock()
    gui = _gui(clock, pre_save_elapsed=50.0)

    GuiSR._sample_walltime_after_round_close(gui, clock)

    assert gui._elapsed_walltime >= 50.0


def test_walltime_measured_from_round_start_ignores_the_previous_value():
    """Even if the round never sampled before, the reading is from the start."""
    clock = _Clock()
    gui = _gui(clock)
    gui._elapsed_walltime = 0.001
    gui._start_timestamp = 900.0

    GuiSR._sample_walltime_after_round_close(gui, clock)

    assert gui._elapsed_walltime == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# The on_update tail must call it, after the recorder saved.
# ---------------------------------------------------------------------------
def test_on_update_tail_samples_after_state_recording():
    import inspect

    source = inspect.getsource(GuiSR.on_update)

    save_at = source.index("_state_recorder.save")
    terminate_at = source.index("if self._terminate:")

    assert terminate_at < save_at
    tail = source[save_at:]
    assert "_sample_walltime_after_round_close" in tail, (
        "the round must re-sample the wall clock after the final save"
    )


def test_on_update_mid_round_sample_still_exists():
    """The overrun check inside the running round is unchanged."""
    import inspect

    source = inspect.getsource(GuiSR.on_update)
    assert "if self._elapsed_walltime > self._max_walltime_limit:" in source
