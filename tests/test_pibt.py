"""Tests for mapf.pibt."""

import pytest

from mapf.grid import parse_map
from mapf.metrics import goal_displacements, is_success, makespan, sum_of_costs
from mapf.pibt import PIBT, TIE_BREAK_RULES, TIE_PAPER
from mapf.validate import validate_solution

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


SWITCHES = [
    {"hindrance": True, "tie_break": "random"},
    {"weighted_choice": True, "tie_break": "random"},
    {"swap_on_failed_push": True},
    {"protect_parked": 0.8, "tie_break": "random"},
    {"goal_lookahead": 3, "tie_break": "random"},
    {"hindrance": True, "swap_on_failed_push": True, "protect_parked": 1.0, "tie_break": "random"},
    {
        "weighted_choice": True,
        "swap_on_failed_push": True,
        "goal_lookahead": 3,
        "tie_break": "random",
    },
]


@pytest.mark.parametrize("switches", SWITCHES)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_step_is_legal_with_switches_on(any_instance, switches, seed):
    solver = PIBT(any_instance.grid, any_instance.starts, any_instance.goals, seed=seed, **switches)
    solution = solver.solve(max_timestep=MAX_T)
    result = validate_solution(
        any_instance.grid, any_instance.starts, any_instance.goals, solution, require_goals=False
    )
    assert result.ok, result.errors


@pytest.mark.parametrize("switches", SWITCHES)
def test_two_by_two_is_solved_with_switches_on(two_by_two, switches):
    solver = PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals, seed=0, **switches)
    assert is_success(solver.solve(max_timestep=MAX_T), two_by_two.goals)


def test_switches_are_off_by_default(two_by_two):
    solver = PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals)
    assert solver.hindrance is False
    assert solver.weighted_choice is False
    assert solver.goal_lookahead == 0
    assert solver.swap_on_failed_push is False
    assert solver.protect_parked == 0.0


def test_hindrance_keeps_a_pushed_agent_out_of_the_pocket_the_pusher_wants():
    grid = parse_map("@@.\n...\n@.@")
    starts, goals = [(1, 0), (1, 1)], [(2, 1), (1, 1)]
    for seed in range(10):
        solver = PIBT(grid, starts, goals, seed=seed, tie_break="random", hindrance=True)
        assert is_success(solver.solve(max_timestep=MAX_T), goals)


@pytest.mark.parametrize("tie_break", TIE_BREAK_RULES)
def test_swap_frees_a_pair_frozen_at_a_dead_end(tie_break):
    grid = parse_map("@@.\n...\n@.@")
    starts, goals = [(1, 0), (2, 1)], [(2, 1), (1, 1)]
    frozen = 0
    for seed in range(10):
        plain = PIBT(grid, starts, goals, seed=seed, tie_break=tie_break)
        frozen += not is_success(plain.solve(max_timestep=60), goals)
        swapping = PIBT(
            grid, starts, goals, seed=seed, tie_break=tie_break, swap_on_failed_push=True
        )
        assert is_success(swapping.solve(max_timestep=60), goals)
    assert frozen > 0


def test_goal_lookahead_cannot_be_negative(two_by_two):
    with pytest.raises(ValueError):
        PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals, goal_lookahead=-1)


def test_weighted_choice_usually_goes_round_a_parked_agent():
    grid = parse_map("...\n...")
    starts, goals = [(0, 0), (0, 1)], [(1, 2), (0, 1)]
    undisturbed = 0
    for seed in range(40):
        solver = PIBT(grid, starts, goals, seed=seed, tie_break="random", weighted_choice=True)
        solution = solver.solve(max_timestep=MAX_T)
        assert is_success(solution, goals)
        undisturbed += goal_displacements(solution, goals) == 0
    assert undisturbed >= 30


def test_weighted_choice_is_reproducible(two_by_two):
    runs = [
        PIBT(
            two_by_two.grid, two_by_two.starts, two_by_two.goals, seed=3, weighted_choice=True
        ).solve(MAX_T)
        for _ in range(2)
    ]
    assert runs[0] == runs[1]


def test_lookahead_holds_an_agent_that_would_be_pushed_off_its_goal():
    grid = parse_map(".....")
    starts, goals = [(0, 0), (0, 2)], [(0, 4), (0, 3)]
    plain = PIBT(grid, starts, goals, seed=0, tie_break="random")
    plain.reset()
    plain.step()
    assert plain.current[1] == (0, 3)
    looking = PIBT(grid, starts, goals, seed=0, tie_break="random", goal_lookahead=4)
    looking.reset()
    looking.step()
    assert looking.holding == {1}
    assert looking.current[1] != (0, 3)


def test_protect_parked_must_be_a_probability(two_by_two):
    with pytest.raises(ValueError):
        PIBT(two_by_two.grid, two_by_two.starts, two_by_two.goals, protect_parked=-0.1)


def test_protect_parked_goes_round_an_agent_resting_on_its_goal():
    grid = parse_map("...\n...")
    starts, goals = [(0, 0), (0, 1)], [(1, 2), (0, 1)]
    for seed in range(10):
        solver = PIBT(grid, starts, goals, seed=seed, tie_break="random", protect_parked=1.0)
        solution = solver.solve(max_timestep=MAX_T)
        assert is_success(solution, goals)
        assert goal_displacements(solution, goals) == 0
