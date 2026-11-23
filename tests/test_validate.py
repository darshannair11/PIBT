"""validate.py: each kind of illegal solution is caught, and a legal one passes."""

from conftest import not_implemented_yet
from mapf.grid import parse_map
from mapf.validate import (
    check_moves,
    check_shape,
    check_starts,
    check_swap_conflicts,
    check_vertex_conflicts,
    validate_solution,
)

pytestmark = not_implemented_yet


def test_legal_solution_passes(two_by_two, two_by_two_solution):
    result = validate_solution(
        two_by_two.grid, two_by_two.starts, two_by_two.goals, two_by_two_solution
    )
    assert result.ok, result.errors
    assert result.errors == []


def test_swap_conflict_is_caught(two_by_two, swap_conflict_solution):
    assert not check_swap_conflicts(swap_conflict_solution).ok
    # nothing else is wrong with it, so the other checks must stay quiet
    assert check_vertex_conflicts(swap_conflict_solution).ok
    assert check_moves(two_by_two.grid, swap_conflict_solution).ok
    result = validate_solution(
        two_by_two.grid, two_by_two.starts, two_by_two.goals, swap_conflict_solution
    )
    assert not result.ok


def test_vertex_conflict_is_caught(corridor_swap, vertex_conflict_solution):
    assert not check_vertex_conflicts(vertex_conflict_solution).ok
    assert check_swap_conflicts(vertex_conflict_solution).ok


def test_jump_is_an_illegal_move(jump_solution):
    grid = parse_map("...")
    assert not check_moves(grid, jump_solution).ok


def test_moving_into_an_obstacle_is_illegal():
    grid = parse_map(".@.")
    assert not check_moves(grid, [[(0, 0)], [(0, 1)]]).ok


def test_leaving_the_grid_is_illegal():
    grid = parse_map("...")
    assert not check_moves(grid, [[(0, 0)], [(-1, 0)]]).ok


def test_wrong_start_is_caught(two_by_two, two_by_two_solution):
    assert not check_starts(two_by_two_solution, [(1, 1), (0, 1)]).ok
    assert check_starts(two_by_two_solution, two_by_two.starts).ok


def test_shape(two_by_two_solution):
    assert check_shape(two_by_two_solution, 2).ok
    assert not check_shape(two_by_two_solution, 3).ok
    assert not check_shape([], 2).ok


def test_unsolved_run_fails_only_the_goal_check(two_by_two, two_by_two_solution):
    unfinished = two_by_two_solution[:2]
    strict = validate_solution(two_by_two.grid, two_by_two.starts, two_by_two.goals, unfinished)
    relaxed = validate_solution(
        two_by_two.grid, two_by_two.starts, two_by_two.goals, unfinished, require_goals=False
    )
    assert not strict.ok
    assert relaxed.ok, relaxed.errors
