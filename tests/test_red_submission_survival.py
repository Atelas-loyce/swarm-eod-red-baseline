"""Real Map01/GuiSR regressions; each scenario owns its OpenGL process.

Only the fixture injects damage. The submitted strategy, sensors, communication,
physics, competition guard and removal lifecycle run unchanged; no mocks.
Zero inventory isolates submission after task completion. Full ten-item rounds
are covered separately by scripts/benchmark_red.py.
"""
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def run_scenario(scenario):
    import numpy as np
    from swarm_rescue.maps.map_01 import Map01
    from swarm_rescue.simulation.elements.sensor_disablers import NoComZone
    from swarm_rescue.simulation.gui_map.gui_sr import GuiSR
    from swarm_rescue.simulation.reporting.team_mode import TeamMode
    from swarm_rescue.simulation.utils.constants import FRAME_RATE
    from swarm_rescue.solutions.my_drone_place_baseline import MyDronePlaceBaseline

    random.seed(17)
    np.random.seed(17)
    the_map = Map01(drone_type=MyDronePlaceBaseline, number_drones=3)
    limit = 240
    the_map._max_timestep_limit = limit
    the_map.clear_bombs()
    for drone in the_map.drones:
        drone._misc_data.team_mode = TeamMode.PLACE
        drone._misc_data.max_timestep_limit = limit
        drone.enable_bomb_deployer(the_map, 0)
    if scenario == "isolated_survivor":
        # A real collision zone disables all radios, including at warm-up.
        the_map.playground.add(NoComZone(size=the_map.size_area),
                               ((0, 0), 0), allow_overlapping=True)
    removed_steps = {}
    try:
        gui = GuiSR(the_map=the_map, headless=True, competition_mode=True)
        while not gui._terminate:
            if gui.elapsed_timestep == 60 and scenario != "healthy":
                victims = the_map.drones[:2] if scenario == "isolated_survivor" else the_map.drones[:1]
                for drone in victims:
                    drone._drone_health = 1
                    drone._last_collision_damage_timestep = None
                    drone.collide_wall()
                    assert drone.removed and drone.drone_health == 0
                    removed_steps[drone.identifier] = drone._step
            if gui.elapsed_timestep == 143 and scenario == "stale_ready":
                # The survivor really received this announcement through radio;
                # the fixture does not write the strategy's message cache.
                assert the_map.drones[2]._peer_ready[1][1] is True
                drone = the_map.drones[1]
                drone._drone_health = 1
                drone._last_collision_damage_timestep = None
                drone.collide_wall()
                assert drone.removed
                removed_steps[drone.identifier] = drone._step
            gui.on_update(FRAME_RATE)
            assert gui.elapsed_timestep <= limit, "Round reached its limit without a submission"
        for identifier, last_step in removed_steps.items():
            assert the_map.drones[identifier]._step == last_step, "Removed drone was driven again"
        submitted = [d for d in the_map.drones if d._exploration_map_submission is not None]
        assert submitted, "No live drone submitted after the primary was removed"
        assert all(not d.removed for d in submitted)
        if scenario == "healthy":
            assert submitted[0].identifier == 0
        elif scenario == "isolated_survivor":
            assert [d.identifier for d in submitted] == [2]
            assert not the_map.drones[2]._peer, "Full-map NoComZone did not isolate the survivor"
        else:
            assert submitted[0].identifier != 0
        if scenario == "stale_ready":
            assert [d.identifier for d in submitted] == [2]
            heard, ready = submitted[0]._peer_ready[1]
            assert ready and submitted[0]._step - heard >= submitted[0].SUBMIT_PEER_TTL
        for drone in submitted:
            grid = drone._exploration_map_submission
            assert grid.shape == (800, 1250) and grid.dtype == np.uint8
            assert np.isin(grid, [0, 1]).all() and np.count_nonzero(grid) > 0
        print("SURVIVAL RESULT " + json.dumps({
            "scenario": scenario, "steps": gui.elapsed_timestep,
            "submitters": [int(d.identifier) for d in submitted],
            "removed": list(removed_steps), "competition_mode": True,
        }), flush=True)
    finally:
        the_map.playground.cleanup()


class SubmissionSurvivalTests(unittest.TestCase):
    def run_real_round(self, scenario):
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--scenario", scenario],
            cwd=ROOT, text=True, capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout, end="")

    def test_healthy_primary(self):
        self.run_real_round("healthy")

    def test_destroyed_primary(self):
        self.run_real_round("destroyed_primary")

    def test_isolated_last_survivor(self):
        self.run_real_round("isolated_survivor")

    def test_ready_peer_dies_before_submitting(self):
        self.run_real_round("stale_ready")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--scenario":
        run_scenario(sys.argv[2])
    else:
        unittest.main()
