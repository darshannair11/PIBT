"""Metrics computed from a solution and from the solver's per-step counters.

None of these are lines of Algorithm 1; each docstring says which part of the
algorithm the number describes.

Rules for the report:
    - compare costs only on instances that both solvers solved;
    - runtime is comparable only between Python implementations.
"""

from __future__ import annotations

import math

from mapf.dist import DistTable
from mapf.grid import Config, Solution
from mapf.pibt import StepStats


def is_success(solution: Solution, goals: Config) -> bool:
    """True when the last configuration is the goal configuration.

    Algorithm 1: the one-shot termination test of section 4.4.1.
    """
    return len(solution) > 0 and len(solution[-1]) == len(goals) and all(
        tuple(u) == tuple(g) for u, g in zip(solution[-1], goals)
    )


def sum_of_costs(solution: Solution, goals: Config) -> int:
    """Sum over agents of the first timestep after which the agent stays on its goal.

    Algorithm 1: quality of the output paths. An agent that is pushed off its
    goal and returns later is charged up to its final arrival. Only meaningful
    when is_success is True; raises ValueError otherwise, so that costs of
    unsolved runs can never reach the results by accident.
    """
    if not is_success(solution, goals):
        raise ValueError("sum_of_costs needs a solved run (last configuration = goals)")
    total = 0
    for i, goal in enumerate(goals):
        goal = tuple(goal)
        # the cost is the timestep right after the agent was last off its goal
        last_off = max((t for t, config in enumerate(solution) if tuple(config[i]) != goal), default=-1)
        total += last_off + 1
    return total


def makespan(solution: Solution) -> int:
    """Number of timesteps taken: len(solution) - 1.

    Algorithm 1: the value of t at termination.
    """
    if len(solution) == 0:
        raise ValueError("empty solution")
    return len(solution) - 1


def sum_of_costs_lower_bound(dist: DistTable, starts: Config) -> int:
    """Sum over agents of dist(s_i, g_i).

    Algorithm 1 Line 10 distances. Denominator of the SOC ratio.
    """
    return sum(dist.get(i, tuple(s)) for i, s in enumerate(starts))


def makespan_lower_bound(dist: DistTable, starts: Config) -> int:
    """Max over agents of dist(s_i, g_i) (T_min in Algorithm 2 Line 1).

    Denominator of the makespan ratio.
    """
    return max((dist.get(i, tuple(s)) for i, s in enumerate(starts)), default=0)


def runtime_per_step(stats: list[StepStats]) -> float:
    """Mean wall-clock seconds per timestep.

    Algorithm 1 Lines 3-7, timed once per t.
    """
    if not stats:
        return math.nan  # no step taken (starts == goals)
    return sum(s.runtime_s for s in stats) / len(stats)


def avg_recursion_depth(stats: list[StepStats]) -> float:
    """Mean recursion depth over all calls of the procedure, across all steps.

    Algorithm 1 Lines 8-22: depth 1 is a call from Line 6, depth 2 is the
    first priority inheritance at Line 16, and so on.
    """
    calls = sum(s.pibt_calls for s in stats)
    if calls == 0:
        return math.nan
    return sum(s.depth_sum for s in stats) / calls


def goal_displacements(solution: Solution, goals: Config) -> int:
    """How many times an agent standing on its goal at t is off it at t+1.

    Algorithm 1 Lines 15-16: a goal agent is displaced when it inherits
    priority from an agent that needs its cell.
    """
    count = 0
    for t in range(len(solution) - 1):
        for i, goal in enumerate(goals):
            goal = tuple(goal)
            if tuple(solution[t][i]) == goal and tuple(solution[t + 1][i]) != goal:
                count += 1
    return count
