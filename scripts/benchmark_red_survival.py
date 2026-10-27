"""Local real-engine Map07 loss scenario. Never include this tool in a ZIP.

The fixture removes drone 0 through the official collision-damage lifecycle.
Truth geometry is read AFTER control ends, for official scoring only. It is
never supplied to the strategy. This is a repeatable fault experiment, not a
reconstruction of the platform run (whose RNG seed was not provided).
"""
import argparse
from dataclasses import asdict
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swarm_rescue.maps.map_07 import Map07
from swarm_rescue.simulation.gui_map.gui_sr import GuiSR
from swarm_rescue.simulation.reporting.place_score_manager import (
    PlaceScoreManager, walls_and_boundary_grid,
)
from swarm_rescue.simulation.reporting.team_mode import TeamMode
from swarm_rescue.simulation.utils.constants import FRAME_RATE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", type=Path, default=ROOT / "src/swarm_rescue/solutions/my_drone_place_baseline.py")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--destroy-step", type=int, default=3000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    spec = importlib.util.spec_from_file_location("survival_strategy", args.strategy)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    random.seed(args.seed)
    np.random.seed(args.seed)
    gc.disable()
    the_map = Map07(drone_type=module.MyDronePlaceBaseline, number_drones=5)
    the_map.clear_bombs()
    for drone in the_map.drones:
        drone._misc_data.team_mode = TeamMode.PLACE
        drone.enable_bomb_deployer(the_map, 2)
    removed_step = None
    try:
        gui = GuiSR(the_map=the_map, headless=True, competition_mode=True)
        while not gui._terminate:
            if gui.elapsed_timestep == args.destroy_step:
                primary = the_map.drones[0]
                assert not primary.removed, "Primary died before the requested injection"
                assert len(the_map.live_bombs) == 10, "Fixture requires all ten tasks complete before loss"
                primary._drone_health = 1
                primary._last_collision_damage_timestep = None
                primary.collide_wall()
                assert primary.removed
                removed_step = primary._step
            gui.on_update(FRAME_RATE)
        assert removed_step is not None, "Round ended before fault injection"
        assert the_map.drones[0]._step == removed_step, "Removed primary was still driven"
        submitters = [d for d in the_map.drones if d._exploration_map_submission is not None]
        prediction = submitters[0]._exploration_map_submission if submitters else None
        walls, boundary = walls_and_boundary_grid(
            the_map.playground, truth_grid=the_map.explored_map.truth_obstacle_grid())
        coverage = the_map.explored_map.score() * 100.0
        scores = PlaceScoreManager().compute_phase1_score(
            walls, prediction, elapsed_walltime=gui.elapsed_walltime,
            max_walltime_limit=the_map.max_walltime_limit,
            score_exploration_trajectory=coverage,
            placed_count=len(the_map.live_bombs), expected_count=10,
            bomb_positions=[tuple(b.true_position()) for b in the_map.live_bombs],
            elapsed_timestep=gui.elapsed_timestep,
            max_timestep_limit=the_map.max_timestep_limit,
            wall_grid=walls, boundary_grid=boundary,
        )
        report = {
            "python": platform.python_version(), "map": "Map07", "seed": args.seed,
            "strategy_sha256": hashlib.sha256(args.strategy.read_bytes()).hexdigest(),
            "engine_commit": subprocess.check_output(
                ["git", "log", "-1", "--format=%H", "--", "src/swarm_rescue/simulation"],
                cwd=ROOT, text=True).strip(),
            "competition_mode": True, "destroy_primary_at": args.destroy_step,
            "steps": gui.elapsed_timestep, "wall_seconds": gui.elapsed_walltime,
            "walltime_limit_reached": gui.is_max_walltime_limit_reached,
            "placed": len(the_map.live_bombs),
            "inventory": sum(d.carried_bombs_count() for d in the_map.drones),
            "destroyed_percent": gui.percent_drones_destroyed,
            "coverage_percent": coverage,
            "submitters": [int(d.identifier) for d in submitters],
            "scores": asdict(scores),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SURVIVAL BENCHMARK " + json.dumps(report), flush=True)
        return int(not submitters or report["walltime_limit_reached"])
    finally:
        the_map.playground.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
