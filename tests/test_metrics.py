"""metrics.py, checked against the hand-written solutions in conftest.py."""

import pytest

from conftest import not_implemented_yet
from mapf.dist import DistTable
from mapf.metrics import (
    avg_recursion_depth,
    goal_displacements,
    is_success,
    makespan,
    makespan_lower_bound,
    runtime_per_step,
    sum_of_costs,
    sum_of_costs_lower_bound,
)
from mapf.pibt import StepStats


def test_two_by_two_solution(two_by_two, two_by_two_solution):
    assert is_success(two_by_two_solution, two_by_two.goals)
    assert makespan(two_by_two_solution) == 3
    assert sum_of_costs(two_by_two_solution, two_by_two.goals) == 4
    assert goal_displacements(two_by_two_solution, two_by_two.goals) == 0


def test_unfinished_solution_is_not_a_success(two_by_two, two_by_two_solution):
    assert not is_success(two_by_two_solution[:2], two_by_two.goals)


@not_implemented_yet  # needs DistTable (Darshan)
def test_lower_bounds(two_by_two):
    dist = DistTable(two_by_two.grid, two_by_two.goals)
    assert sum_of_costs_lower_bound(dist, two_by_two.starts) == 2
    assert makespan_lower_bound(dist, two_by_two.starts) == 1


def test_agent_already_on_goal_costs_nothing(on_goal):
    solution = [list(on_goal.starts)]
    assert is_success(solution, on_goal.goals)
    assert makespan(solution) == 0
    assert sum_of_costs(solution, on_goal.goals) == 0


def test_leaving_the_goal_and_returning(displaced_solution):
    goals = [(0, 0), (0, 1)]
    assert is_success(displaced_solution, goals)
    assert sum_of_costs(displaced_solution, goals) == 2  # a1 is charged until its final arrival
    assert goal_displacements(displaced_solution, goals) == 1


def test_step_counters():
    stats = [
        StepStats(runtime_s=0.002, pibt_calls=2, depth_sum=3, max_depth=2),
        StepStats(runtime_s=0.004, pibt_calls=2, depth_sum=5, max_depth=3),
    ]
    assert runtime_per_step(stats) == pytest.approx(0.003)
    assert avg_recursion_depth(stats) == pytest.approx(8 / 4)


def test_sum_of_costs_refuses_an_unsolved_run(two_by_two, two_by_two_solution):
    with pytest.raises(ValueError):
        sum_of_costs(two_by_two_solution[:2], two_by_two.goals)


def test_no_steps_gives_nan_not_a_crash():
    import math

    assert math.isnan(runtime_per_step([]))
    assert math.isnan(avg_recursion_depth([]))
