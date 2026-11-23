"""Metrics computed from a solution and from the solver's per-step counters.

None of these are lines of Algorithm 1; each docstring says which part of the
algorithm the number describes.

Rules for the report (see CLAUDE.md):
    - compare costs only on instances that both solvers solved;
    - runtime is comparable only between Python implementations.
"""

from __future__ import annotations

from mapf.dist import DistTable
from mapf.grid import Config, Solution
from mapf.pibt import StepStats


def is_success(solution: Solution, goals: Config) -> bool:
    """True when the last configuration is the goal configuration.

    Algorithm 1: the one-shot termination test of section 4.4.1.
    """
    # TODO(Person A)
    raise NotImplementedError


def sum_of_costs(solution: Solution, goals: Config) -> int:
    """Sum over agents of the first timestep after which the agent stays on its goal.

    Algorithm 1: quality of the output paths. An agent that is pushed off its
    goal and returns later is charged up to its final arrival. Only meaningful
    when is_success is True.
    """
    # TODO(Person A)
    raise NotImplementedError


def makespan(solution: Solution) -> int:
    """Number of timesteps taken: len(solution) - 1.

    Algorithm 1: the value of t at termination.
    """
    # TODO(Person A)
    raise NotImplementedError


def sum_of_costs_lower_bound(dist: DistTable, starts: Config) -> int:
    """Sum over agents of dist(s_i, g_i).

    Algorithm 1 Line 10 distances. Denominator of the SOC ratio.
    """
    # TODO(Person A)
    raise NotImplementedError


def makespan_lower_bound(dist: DistTable, starts: Config) -> int:
    """Max over agents of dist(s_i, g_i) (T_min in Algorithm 2 Line 1).

    Denominator of the makespan ratio.
    """
    # TODO(Person A)
    raise NotImplementedError


def runtime_per_step(stats: list[StepStats]) -> float:
    """Mean wall-clock seconds per timestep.

    Algorithm 1 Lines 3-7, timed once per t.
    """
    # TODO(Person A)
    raise NotImplementedError


def avg_recursion_depth(stats: list[StepStats]) -> float:
    """Mean recursion depth over all calls of the procedure, across all steps.

    Algorithm 1 Lines 8-22: depth 1 is a call from Line 6, depth 2 is the
    first priority inheritance at Line 16, and so on.
    """
    # TODO(Person A)
    raise NotImplementedError


def goal_displacements(solution: Solution, goals: Config) -> int:
    """How many times an agent standing on its goal at t is off it at t+1.

    Algorithm 1 Lines 15-16: a goal agent is displaced when it inherits
    priority from an agent that needs its cell.
    """
    # TODO(Person A)
    raise NotImplementedError
