"""BFS distance tables, one per goal.

Paper section 4.4.1 ("Distance evaluation"): instead of searching on demand,
run one breadth-first search from each agent's goal before planning, at a
total cost of O(|A| * |E|). Algorithm 1 Line 10 then reads dist(u, g_i) from
the table.
"""

from __future__ import annotations

import numpy as np

from mapf.grid import Config, Coord, Grid

# Value stored for cells that cannot reach the goal (and for obstacles).
UNREACHABLE: int = int(np.iinfo(np.int32).max)


def bfs_distances(grid: Grid, goal: Coord) -> np.ndarray:
    """Shortest-path length from every cell to goal, ignoring other agents.

    Algorithm 1 Line 10: this is dist(u, g_i) for all u at once.
    Returns an int32 array shaped like grid.free; unreachable cells and
    obstacles hold UNREACHABLE.
    """
    # TODO(Darshan): breadth-first search outward from goal.
    raise NotImplementedError


class DistTable:
    """Distance tables for all agents.

    Algorithm 1 Line 10: get(i, u) is dist(u, g_i).
    """

    def __init__(self, grid: Grid, goals: Config) -> None:
        """Store the inputs. Algorithm 1: precomputation before Line 1."""
        self.grid = grid
        self.goals = goals
        # TODO(Darshan): decide between building every table here (eager) and
        # growing each BFS on demand (lazy, which is what pypibt does).

    def get(self, agent: int, cell: Coord) -> int:
        """dist(cell, g_agent). Algorithm 1 Line 10."""
        # TODO(Darshan)
        raise NotImplementedError
