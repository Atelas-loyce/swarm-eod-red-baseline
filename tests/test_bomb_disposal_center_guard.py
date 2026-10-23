"""A bomb must never be swallowed by the disposal center without being scored.

Checked against the real Map01 geometry:

1. `MapAbstract.spawn_bombs` drops a bombs-file entry that starts in contact
   with the disposal center, because such a bomb is disposed by the first
   physics step and is not something the round can search for and rescue.
2. A bomb that still reaches the playground in contact with the center (the
   path a legacy bombs file takes) is disposed during the warm-up step, and
   that disposal must be counted -- the round's score depends on it.

Both checks share one map and one window: arcade cannot reliably open a new
Window after the previous one was closed in the same process.
"""

from swarm_rescue.maps.map_01 import Map01
from swarm_rescue.simulation.drone.drone_motionless import DroneMotionless
from swarm_rescue.simulation.elements.bomb import Bomb
from swarm_rescue.simulation.gui_map.gui_sr import GuiSR


def test_bomb_on_the_disposal_center_is_never_swallowed():
    the_map = Map01(drone_type=DroneMotionless, number_drones=2)
    try:
        the_map.clear_bombs()
        dc_x, dc_y = the_map._disposal_center_pos[0]

        # 1. A bombs-file entry on the center is dropped at spawn.
        the_map.spawn_bombs([
            {"x": float(dc_x), "y": float(dc_y), "theta": 0.0},
            {"x": 400.0, "y": 0.0, "theta": 0.0},
        ])
        assert the_map.number_bombs == 1
        assert [float(b.true_position()[0]) for b in the_map.live_bombs] == [400.0]

        # 2. A bomb that still starts on the center is disposed on the warm-up
        #    step and counted, so the round can complete its disposal.
        the_map.clear_bombs()
        bomb = Bomb(disposal_center=the_map.disposal_center)
        the_map._bombs.append(bomb)
        the_map._number_bombs = 1
        the_map.playground.add(bomb, ((float(dc_x), float(dc_y)), 0.0))

        gui = GuiSR(the_map=the_map, headless=True)
        gui.on_update(0.03)

        assert bomb.removed is True
        assert bomb.disposed is True
        assert gui.disposed_number == 1
        assert gui.total_number_bombs == 1
        assert gui.full_disposal_timestep == 1
        assert gui._terminate is True
    finally:
        the_map.playground.cleanup()
