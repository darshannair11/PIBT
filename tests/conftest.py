"""Tiny hand-made instances and solutions shared by the tests.

Coordinates are (row, col). Each fixture's docstring says what should happen,
so the expected values in the tests can be checked by hand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mapf.grid import Instance, parse_map

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

# Marker for tests of code that is still a stub. A test carrying it shows as
# "xfailed" while the body raises NotImplementedError, as "xpassed" once the
# code works, and as a real failure if the code runs but gives a wrong answer.
# Remove the marker from a test file once everything in it passes.
not_implemented_yet = pytest.mark.xfail(
    raises=NotImplementedError, reason="stub not implemented yet"
)


# ---------------------------------------------------------------------------
# Instances
# ---------------------------------------------------------------------------


@pytest.fixture
def corridor_swap() -> Instance:
    """Two agents must swap ends of a 1x3 corridor.

        a0 . a1        a0: (0,0) -> (0,2)      a1: (0,2) -> (0,0)

    Unsolvable (no room to pass). PIBT must never produce a vertex or swap
    conflict here and must end unsolved at the time limit.
    """
    grid = parse_map("...", name="corridor-1x3")
    return Instance(grid, starts=[(0, 0), (0, 2)], goals=[(0, 2), (0, 0)], name="corridor_swap")


@pytest.fixture
def two_by_two() -> Instance:
    """Two adjacent agents must exchange cells on a 2x2 grid.

        a0 a1          a0: (0,0) -> (0,1)      a1: (0,1) -> (0,0)
        .  .

    Solvable only by going round the cycle, never by a direct swap. This is
    the smallest case that needs priority inheritance (Lines 15-16) and the
    swap check (Line 13). Lower bounds: sum of costs 2, makespan 1.
    """
    grid = parse_map("..\n..", name="grid-2x2")
    return Instance(grid, starts=[(0, 0), (0, 1)], goals=[(0, 1), (0, 0)], name="two_by_two")


@pytest.fixture
def dead_end() -> Instance:
    """An agent sits on its goal between another agent and that agent's goal.

        a0 a1 .        a0: (0,0) -> (0,2)      a1: (0,1) -> (0,1)

    a1 can be pushed into the dead end at (0,2), after which it has no escape
    and its call returns invalid (Lines 20-21). This is the failure case of
    the paper's Fig. 5: unsolvable, but every step must still be legal.
    """
    grid = parse_map("...", name="corridor-1x3")
    return Instance(grid, starts=[(0, 0), (0, 1)], goals=[(0, 2), (0, 1)], name="dead_end")


@pytest.fixture
def on_goal() -> Instance:
    """One agent that starts on its goal in the middle of an open 3x3 grid.

    The solution is the start configuration alone: makespan 0, sum of costs 0.
    """
    grid = parse_map("...\n...\n...", name="grid-3x3")
    return Instance(grid, starts=[(1, 1)], goals=[(1, 1)], name="on_goal")


@pytest.fixture(params=["corridor_swap", "two_by_two", "dead_end", "on_goal"])
def any_instance(request) -> Instance:
    """Each of the four instances in turn."""
    return request.getfixturevalue(request.param)


# ---------------------------------------------------------------------------
# Hand-written solutions (for the validator and the metrics)
# ---------------------------------------------------------------------------


@pytest.fixture
def two_by_two_solution() -> list:
    """A legal solution of two_by_two: a1 goes round the cycle.

        t=0  a0 (0,0)  a1 (0,1)
        t=1  a0 (0,1)  a1 (1,1)
        t=2  a0 (0,1)  a1 (1,0)
        t=3  a0 (0,1)  a1 (0,0)

    makespan 3; sum of costs 1 + 3 = 4; no goal displacements.
    """
    return [
        [(0, 0), (0, 1)],
        [(0, 1), (1, 1)],
        [(0, 1), (1, 0)],
        [(0, 1), (0, 0)],
    ]


@pytest.fixture
def swap_conflict_solution() -> list:
    """two_by_two "solved" by a direct swap: illegal (swap conflict at t=0 -> 1)."""
    return [
        [(0, 0), (0, 1)],
        [(0, 1), (0, 0)],
    ]


@pytest.fixture
def vertex_conflict_solution() -> list:
    """corridor_swap where both agents step into the middle cell: illegal at t=1."""
    return [
        [(0, 0), (0, 2)],
        [(0, 1), (0, 1)],
    ]


@pytest.fixture
def jump_solution() -> list:
    """One agent on the 1x3 corridor moving two cells in one step: illegal move."""
    return [
        [(0, 0)],
        [(0, 2)],
    ]


@pytest.fixture
def displaced_solution() -> list:
    """A legal walk on the 1x3 corridor where a1 leaves its goal and comes back.

    Use with starts [(0,0), (0,1)] and goals [(0,0), (0,1)]:

        t=0  a0 (0,0)  a1 (0,1)
        t=1  a0 (0,0)  a1 (0,2)
        t=2  a0 (0,0)  a1 (0,1)

    makespan 2; sum of costs 0 + 2 = 2; one goal displacement (a1 at t=0).
    """
    return [
        [(0, 0), (0, 1)],
        [(0, 0), (0, 2)],
        [(0, 0), (0, 1)],
    ]
