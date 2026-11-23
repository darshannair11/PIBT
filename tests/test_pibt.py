"""pibt.py: behaviour on the four hand-made instances (Algorithm 1).

These need grid, dist, validate and metrics as well, so they are the last
tests to turn green.
"""

import pytest

from conftest import not_implemented_yet
from mapf.metrics import goal_displacements, is_success, makespan, sum_of_costs
from mapf.pibt import PIBT, TIE_BREAK_RULES, TIE_PAPER
from mapf.validate import validate_solution

pytestmark = not_implemented_yet

MAX_T = 20
SEEDS = range(5)


def solve(inst, seed=0, tie_break=TIE_PAPER, max_timestep=MAX_T):
    solver = PIBT(inst.grid, inst.starts, inst.goals, seed=seed, tie_break=tie_break)
    return solver, solver.solve(max_timestep=max_timestep)


@pytest.mark.parametrize("tie_break", TIE_BREAK_RULES)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_step_is_legal(any_instance, tie_break, seed):
    """Lines 9, 12, 13: legal moves, no vertex conflict, no swap conflict, solved or not."""
    _, solution = solve(any_instance, seed, tie_break)
    result = validate_solution(
        any_instance.grid, any_instance.starts, any_instance.goals, solution, require_goals=False
    )
    assert result.ok, result.errors
    assert solution[0] == any_instance.starts  # Line 1
    assert makespan(solution) <= MAX_T


@pytest.mark.parametrize("tie_break", TIE_BREAK_RULES)
@pytest.mark.parametrize("seed", SEEDS)
def test_two_by_two_is_solved_round_the_cycle(two_by_two, tie_break, seed):
    """Lines 13, 15-16: the blocked agent inherits priority and goes round."""
    _, solution = solve(two_by_two, seed, tie_break)
    assert is_success(solution, two_by_two.goals)
    assert validate_solution(two_by_two.grid, two_by_two.starts, two_by_two.goals, solution).ok
    assert sum_of_costs(solution, two_by_two.goals) >= 4  # 2 if a direct swap were allowed


@pytest.mark.parametrize("seed", SEEDS)
def test_corridor_swap_is_not_solved(corridor_swap, seed):
    """Unsolvable instance: the run stops at the time limit without conflicts."""
    _, solution = solve(corridor_swap, seed)
    assert not is_success(solution, corridor_swap.goals)
    assert makespan(solution) == MAX_T


@pytest.mark.parametrize("seed", SEEDS)
def test_dead_end_is_not_solved_and_displaces_the_goal_agent(dead_end, seed):
    """Lines 15-16 then 20-21: a1 is pushed off its goal into the dead end, then stuck."""
    _, solution = solve(dead_end, seed)
    assert not is_success(solution, dead_end.goals)
    assert goal_displacements(solution, dead_end.goals) >= 1


def test_agent_on_goal_needs_no_steps(on_goal):
    """Termination (section 4.4.1): already at the goal configuration."""
    solver, solution = solve(on_goal)
    assert solution == [on_goal.starts]
    assert solver.stats == []


def test_same_seed_same_solution(two_by_two):
    """The Line 10 random tie-break is driven only by the seed."""
    _, first = solve(two_by_two, seed=7)
    _, second = solve(two_by_two, seed=7)
    assert first == second


def test_one_stats_entry_per_step(two_by_two):
    solver, solution = solve(two_by_two)
    assert len(solver.stats) == makespan(solution)
    assert all(s.pibt_calls >= 1 and s.max_depth >= 1 for s in solver.stats)


def test_priorities_start_distinct_in_unit_interval(two_by_two):
    """Line 2: epsilon_i in [0, 1), all different."""
    solver = PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals, seed=0)
    eps = solver.init_priorities()
    assert len(eps) == 2 and len(set(eps)) == 2
    assert all(0 <= e < 1 for e in eps)


def test_unknown_tie_break_is_rejected(two_by_two):
    with pytest.raises(ValueError):
        PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals, tie_break="nope")
