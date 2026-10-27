from swarm_rescue.simulation.gui_map.gui_sr import GuiSR


class _BombStub:
    """Bomb stub exposing the only field the round counts."""

    def __init__(self, disposed: bool = False):
        self.disposed = disposed


class _PlaygroundStub:
    """Playground stub whose step disposes the given number of bombs."""

    def __init__(self, bomb_count: int, dispose_on_step: int):
        self.bombs = [_BombStub() for _ in range(bomb_count)]
        self._dispose_on_step = dispose_on_step

    def step(self, all_commands=None, all_messages=None):
        for bomb in self.bombs[:self._dispose_on_step]:
            bomb.disposed = True
        return None, {}


def _gui_for_warmup(total_bombs: int, dispose_on_step: int = 1):
    gui = object.__new__(GuiSR)
    gui._editing_locked = False
    gui._elapsed_timestep = 0
    gui._drones_commands = {}
    gui._messages = None
    gui._total_number_bombs = total_bombs
    gui._disposed_number = 0
    gui._full_disposal_timestep = 0
    gui._terminate = False
    gui._playground = _PlaygroundStub(total_bombs, dispose_on_step)
    gui._the_map = _MapStub(gui._playground)
    return gui


class _MapStub:
    def __init__(self, playground):
        self.bombs = playground.bombs


def test_warmup_step_counts_the_bomb_it_disposed():
    gui = _gui_for_warmup(total_bombs=3, dispose_on_step=1)

    gui.on_update(0.03)

    assert gui.elapsed_timestep == 1
    assert gui.disposed_number == 1
    assert gui.full_disposal_timestep == 0
    assert gui._terminate is False


def test_warmup_step_completes_a_round_whose_bombs_all_start_on_the_center():
    gui = _gui_for_warmup(total_bombs=1, dispose_on_step=1)

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

    # The round reports its running total of disposed bombs.
    gui._update_disposal_progress(disposed_count=3)

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

    gui._update_disposal_progress(disposed_count=3)

    assert gui._disposed_number == 3
    assert gui._full_disposal_timestep == 0
    assert gui._terminate is False
