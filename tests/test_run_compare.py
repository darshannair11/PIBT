"""experiments/run_compare.py: summarise on hand-made rows, and our validator on pypibt output."""

import pytest

from conftest import DATA_DIR
from experiments.run_compare import RunRow, summarise


def _row(solver, rep, success, soc=None, lb=10):
    return RunRow(
        "m", "m-random-1", 5, rep, 0, solver, success=success, valid=True,
        sum_of_costs=soc, makespan=soc and 4, soc_lower_bound=lb, makespan_lower_bound=4,
        runtime_per_step_s=0.001, goal_displacements=0,
    )


def test_summarise_uses_only_runs_every_solver_solved():
    rows = [
        _row("ours-paper", 0, True, 20), _row("pypibt", 0, True, 10),
        # rep 1: only ours solved it, so its cost (60) must not enter the ratio
        _row("ours-paper", 1, True, 60), _row("pypibt", 1, False),
    ]
    text = summarise(rows)
    assert "1 of 2 runs solved by every solver" in text
    ours = next(ln for ln in text.splitlines() if "ours-paper" in ln)
    theirs = next(ln for ln in text.splitlines() if "pypibt" in ln)
    assert "2/2" in ours and "2.000" in ours  # 20 / 10, not (20/10 + 60/10) / 2
    assert "1/2" in theirs and "1.000" in theirs


def test_summarise_flags_invalid_rows():
    bad = _row("pypibt", 0, False)
    bad.valid = False
    assert "WARNING: 1 invalid" in summarise([bad])


@pytest.mark.parametrize("n", [10, 32])
def test_our_validator_accepts_pypibt_on_empty_8_8(n):
    """Cross-check of the validator itself: pypibt's solutions must pass it."""
    pytest.importorskip("numpy")
    from experiments.crosscheck import PYPIBT_SRC, run_pypibt
    from mapf.grid import load_instance
    from mapf.metrics import is_success
    from mapf.validate import validate_solution

    if not (PYPIBT_SRC / "pypibt").is_dir():
        pytest.skip("pypibt submodule not checked out")
    map_path = DATA_DIR / "maps" / "empty-8-8.map"
    scen_path = DATA_DIR / "scens" / "empty-8-8-random-1.scen"
    inst = load_instance(map_path, scen_path, n)
    result = run_pypibt(map_path, scen_path, n, seed=0, max_timestep=500)
    check = validate_solution(inst.grid, inst.starts, inst.goals, result.solution, require_goals=False)
    assert check.ok, check.errors
    assert is_success(result.solution, inst.goals) == result.reached_goals
