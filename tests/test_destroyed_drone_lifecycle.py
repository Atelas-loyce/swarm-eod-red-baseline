#!/usr/bin/env python3
"""
Tests for the lifecycle of a destroyed drone.

When a drone's health reaches zero it is removed from the playground, but the
round loop must then stop driving it: no ``control()`` call, no message, and no
stale ``playground.agents`` cache entry, so the health statistics that are
computed from ``playground.agents`` stay meaningful.
"""
from types import SimpleNamespace

import pytest

from swarm_rescue.simulation.drone.ground_truth_guard import run_control
from swarm_rescue.simulation.gui_map.gui_sr import GuiSR
from swarm_rescue.simulation.gui_map.playground import Playground


class _Drone:
    """Stand-in with the attributes the round loop and cleanup touch."""

    def __init__(self, identifier, health=50):
        self.identifier = identifier
        self._drone_health = health
        self.removed = False
        self.control_calls = 0
        self.message_calls = 0
        self.elapsed_walltime = 0
        self.elapsed_timestep = 0
        self._exploration_map_submission = None
        self.communicator = f"comm-{identifier}"

    @property
    def drone_health(self):
        return self._drone_health

    def control(self):
        self.control_calls += 1
        return {}

    def define_message_for_all(self):
        self.message_calls += 1
        return {"probe": self.identifier}


def _gui(drones):
    return SimpleNamespace(
        _drones=drones,
        _number_drones=len(drones),
    )


# ---------------------------------------------------------------------------
# The loop must skip destroyed drones.
# ---------------------------------------------------------------------------
def test_control_loop_skips_removed_drone():
    alive_a, dead, alive_b = _Drone(0), _Drone(1), _Drone(2)
    dead.removed = True
    gui = _gui([alive_a, dead, alive_b])

    driven = GuiSR._drivable_drones(gui)
    for drone in driven:
        run_control(drone)

    assert dead.control_calls == 0
    assert alive_a.control_calls == 1
    assert alive_b.control_calls == 1


def test_control_loop_keeps_drone_order():
    drones = [_Drone(identifier) for identifier in range(5)]
    drones[2].removed = True
    gui = _gui(drones)

    assert [d.identifier for d in GuiSR._drivable_drones(gui)] == [0, 1, 3, 4]


def test_message_collection_skips_removed_drone():
    alive_a, dead, alive_b = _Drone(0), _Drone(1), _Drone(2)
    dead.removed = True
    gui = _gui([alive_a, dead, alive_b])

    sent = {}
    for drone in GuiSR._drivable_drones(gui):
        sent[drone] = {None: drone.define_message_for_all()}

    assert dead.message_calls == 0
    assert set(sent) == {alive_a, alive_b}


def test_drivable_drones_returns_everything_while_all_alive():
    drones = [_Drone(identifier) for identifier in range(4)]
    gui = _gui(drones)

    assert GuiSR._drivable_drones(gui) == drones


def test_drivable_drones_does_not_consume_a_generator():
    """The helper returns a concrete list usable more than once."""
    drones = [_Drone(0), _Drone(1)]
    gui = _gui(drones)

    driven = GuiSR._drivable_drones(gui)
    assert isinstance(driven, list)
    assert len(driven) == 2
    assert len(GuiSR._drivable_drones(gui)) == 2


# ---------------------------------------------------------------------------
# playground.agents must not serve a stale cache after a plain remove().
# ---------------------------------------------------------------------------
def _agents_view(agents, needs_update):
    return SimpleNamespace(
        _agents=agents,
        _cached_agents=list(agents),
        _agents_cache_needs_update=needs_update,
    )


def test_agents_cache_reflects_plain_removal():
    alive = _Drone(0)
    dying = _Drone(1)
    view = _agents_view([alive, dying], needs_update=False)

    assert Playground.agents.fget(view) == [alive, dying]

    # A plain remove (the path collide_wall uses) only sets `removed`.
    dying.removed = True

    assert Playground.agents.fget(view) == [alive]


def test_agents_cache_reflects_definitive_removal():
    alive = _Drone(0)
    dying = _Drone(1)
    view = _agents_view([alive, dying], needs_update=True)

    dying.removed = True

    assert Playground.agents.fget(view) == [alive]


def test_agents_cache_is_reused_while_nothing_changes():
    alive = _Drone(0)
    view = _agents_view([alive], needs_update=False)

    first = Playground.agents.fget(view)
    second = Playground.agents.fget(view)

    assert first is second


# ---------------------------------------------------------------------------
# Health statistics count the destroyed drones.
# ---------------------------------------------------------------------------
def _playground_with(agents):
    return SimpleNamespace(agents=agents)


def test_health_stats_count_destroyed_drones():
    alive = _Drone(0, health=50)
    alive_a = _Drone(1, health=30)
    dead = _Drone(2, health=0)
    dead.removed = True

    gui = SimpleNamespace(
        _drones=[alive, alive_a, dead],
        _playground=_playground_with([alive, alive_a]),
        _number_drones=3,
        _mean_drones_health=0.0,
        _percent_drones_destroyed=0.0,
    )

    GuiSR.compute_health_stats(gui)

    assert gui._percent_drones_destroyed == pytest.approx(100 / 3)
    # Mean over every drone in the round, the destroyed one counting as 0.
    assert gui._mean_drones_health == pytest.approx((50 + 30) / 3)


def test_health_stats_with_no_loss():
    alive = [_Drone(i, health=50) for i in range(4)]
    gui = SimpleNamespace(
        _drones=alive,
        _playground=_playground_with(alive),
        _number_drones=4,
        _mean_drones_health=0.0,
        _percent_drones_destroyed=0.0,
    )

    GuiSR.compute_health_stats(gui)

    assert gui._percent_drones_destroyed == 0.0
    assert gui._mean_drones_health == pytest.approx(50.0)


def test_health_stats_when_every_drone_is_destroyed():
    drones = [_Drone(i, health=0) for i in range(3)]
    for drone in drones:
        drone.removed = True

    gui = SimpleNamespace(
        _drones=drones,
        _playground=_playground_with([]),
        _number_drones=3,
        _mean_drones_health=0.0,
        _percent_drones_destroyed=0.0,
    )

    GuiSR.compute_health_stats(gui)

    assert gui._percent_drones_destroyed == 100.0
    assert gui._mean_drones_health == 0.0


def test_health_stats_without_drones_keeps_defaults():
    gui = SimpleNamespace(
        _drones=[],
        _playground=_playground_with([]),
        _number_drones=0,
        _mean_drones_health=0.0,
        _percent_drones_destroyed=0.0,
    )

    GuiSR.compute_health_stats(gui)

    assert gui._percent_drones_destroyed == 0.0


# ---------------------------------------------------------------------------
# Every consumer of the roster skips the destroyed drone.
# ---------------------------------------------------------------------------
def test_exploration_and_display_use_the_drivable_roster():
    """update_drones / submission scan / display must not touch a removed drone."""
    import inspect

    source = inspect.getsource(GuiSR.on_update)

    assert "explored_map.update_drones(drivable_drones)" in source
    assert "explored_map.update_drones(self._drones)" not in source
    assert "for drone in drivable_drones\n" in source
    assert "self._drones[0].display()" not in source


def test_message_collection_covers_exactly_the_drivable_drones():
    alive_a, dead, alive_b = _Drone(0), _Drone(1), _Drone(2)
    dead.removed = True
    gui = _gui([alive_a, dead, alive_b])

    messages = GuiSR.collect_all_messages(gui, GuiSR._drivable_drones(gui))

    assert set(messages) == {alive_a, alive_b}
    assert alive_a.message_calls == 1
    assert alive_b.message_calls == 1
    assert dead.message_calls == 0


def test_commands_are_only_recorded_for_drivable_drones():
    alive_a, dead = _Drone(0), _Drone(1)
    dead.removed = True
    gui = _gui([alive_a, dead])
    gui._drones_commands = {}

    for drone in GuiSR._drivable_drones(gui):
        gui._drones_commands[drone] = run_control(drone)

    assert set(gui._drones_commands) == {alive_a}
    assert dead.control_calls == 0
