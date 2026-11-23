from __future__ import annotations

from collections import deque

import numpy as np

from mapf.grid import Config, Coord, Grid, neighbours

UNREACHABLE = 10**9


def bfs_distances(grid: Grid, goal: Coord) -> np.ndarray:
    # Algorithm 1, Line 10: dist(u, g_i)
    distances = np.full(grid.free.shape, UNREACHABLE, dtype=np.int32)
    distances[goal] = 0
    queue = deque()
    queue.append(goal)
    while queue:
        current_cell = queue.popleft()
        for next_cell in neighbours(grid, current_cell):
            if distances[next_cell] == UNREACHABLE:
                distances[next_cell] = distances[current_cell] + 1
                queue.append(next_cell)
    return distances


class DistTable:
    def __init__(self, grid: Grid, goals: Config) -> None:
        self.grid = grid
        self.goals = goals
        self.tables = [bfs_distances(self.grid, goal) for goal in self.goals]

    def get(self, agent: int, cell: Coord) -> int:
        # Algorithm 1, Line 10: dist(u, g_i)
        return self.tables[agent][cell]
