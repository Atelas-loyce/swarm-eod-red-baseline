from swarm_rescue.simulation.gui_map.gui_sr import GuiSR


class _PlaygroundStub:
    """Playground stub whose step grants the given total reward."""

    def __init__(self, reward: float):
        self.reward = reward

    def step(self, all_commands=None, all_messages=None):
        return None, {object(): self.reward}


def _gui_for_warmup(total_bombs: int, reward: float):
    gui = object.__new__(GuiSR)
    gui._editing_locked = False
    gui._elapsed_timestep = 0
    gui._drones_commands = {}
    gui._messages = None
    gui._total_number_bombs = total_bombs
    gui._disposed_number = 0
    gui._full_disposal_timestep = 0
    gui._terminate = False
    gui._playground = _PlaygroundStub(reward)
    return gui


def test_warmup_step_counts_the_bomb_it_disposed():
    gui = _gui_for_warmup(total_bombs=3, reward=1.0)

    gui.on_update(0.03)

    assert gui.elapsed_timestep == 1
    assert gui.disposed_number == 1
    assert gui.full_disposal_timestep == 0
    assert gui._terminate is False


def test_warmup_step_completes_a_round_whose_bombs_all_start_on_the_center():
    gui = _gui_for_warmup(total_bombs=1, reward=1.0)

    gui.on_update(0.03)

    assert gui.disposed_number == 1
    assert gui.full_disposal_timestep == 1
    assert gui._terminate is True


def test_update_disposal_progress_marks_termination_when_all_bombs_disposed():
    gui = object.__new__(GuiSR)
    gui._total_number_bombs = 3
    gui._disposed_number = 2
    gui._full_disposal_timestep = 0
    gui._elapsed_timestep = 42
    gui._terminate = False

    gui._update_disposal_progress(new_reward=1)

    assert gui._disposed_number == 3
    assert gui._full_disposal_timestep == 42
    assert gui._terminate is True


def test_update_disposal_progress_does_not_terminate_before_completion():
    gui = object.__new__(GuiSR)
    gui._total_number_bombs = 5
    gui._disposed_number = 2
    gui._full_disposal_timestep = 0
    gui._elapsed_timestep = 42
    gui._terminate = False

    gui._update_disposal_progress(new_reward=1)

    assert gui._disposed_number == 3
    assert gui._full_disposal_timestep == 0
    assert gui._terminate is False
