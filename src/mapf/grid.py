from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import numpy as np

Coord: TypeAlias = tuple[int, int]
Config: TypeAlias = list[Coord]
Solution: TypeAlias = list[Config]

PASSABLE_CHARS = frozenset(".GS")


@dataclass(frozen=True)
class Grid:
    free: np.ndarray
    name: str = ""

    @property
    def height(self) -> int:
        return int(self.free.shape[0])

    @property
    def width(self) -> int:
        return int(self.free.shape[1])


@dataclass(frozen=True)
class Instance:
    grid: Grid
    starts: Config
    goals: Config
    name: str = ""

    @property
    def num_agents(self) -> int:
        return len(self.starts)


def parse_map(text: str, name: str = "") -> Grid:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if "map" in lines:
        rows = lines[lines.index("map") + 1 :]
    else:
        rows = lines
    if not rows:
        raise ValueError(f"map {name!r} has no rows")

    height = len(rows)
    width = len(rows[0])
    for line in lines:
        words = line.split()
        if len(words) != 2:
            continue
        if words[0] == "height" and int(words[1]) != height:
            raise ValueError(f"map {name!r}: header says {words[1]} rows, found {height}")
        if words[0] == "width":
            width = int(words[1])

    free = np.zeros((height, width), dtype=bool)
    for row, row_text in enumerate(rows):
        if len(row_text) != width:
            raise ValueError(f"map {name!r}: row {row} has {len(row_text)} cells, expected {width}")
        for column, char in enumerate(row_text):
            free[row, column] = char in PASSABLE_CHARS
    free.setflags(write=False)
    return Grid(free=free, name=name)


def load_map(path: str | Path) -> Grid:
    path = Path(path)
    return parse_map(path.read_text(), name=path.stem)


def load_scen(path: str | Path, num_agents: int | None = None) -> tuple[Config, Config]:
    starts: Config = []
    goals: Config = []
    for line in Path(path).read_text().splitlines():
        columns = line.split()
        if len(columns) != 9:
            continue
        start_x, start_y, goal_x, goal_y = map(int, columns[4:8])
        starts.append((start_y, start_x))
        goals.append((goal_y, goal_x))
        if len(starts) == num_agents:
            break
    if num_agents is not None and len(starts) < num_agents:
        raise ValueError(f"{path}: asked for {num_agents} agents, file has {len(starts)}")
    return starts, goals


def load_instance(
    map_path: str | Path, scen_path: str | Path, num_agents: int | None = None
) -> Instance:
    grid = load_map(map_path)
    starts, goals = load_scen(scen_path, num_agents)
    name = f"{Path(scen_path).stem}|agents={len(starts)}"
    return Instance(grid=grid, starts=starts, goals=goals, name=name)


def is_free(grid: Grid, cell: Coord) -> bool:
    row, column = cell
    if not (0 <= row < grid.height and 0 <= column < grid.width):
        return False
    return bool(grid.free[row, column])


def neighbours(grid: Grid, cell: Coord) -> list[Coord]:
    # Algorithm 1, Line 9: Neigh()
    neighbour_indexes = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    final_neighbours = []
    for row, column in neighbour_indexes:
        neighbour_cell = (cell[0] + row, cell[1] + column)
        if is_free(grid, neighbour_cell):
            final_neighbours.append(neighbour_cell)
    return final_neighbours


def free_cells(grid: Grid) -> list[Coord]:
    free_cells_list = []
    for row in range(grid.height):
        for column in range(grid.width):
            if is_free(grid, (row, column)):
                free_cells_list.append((row, column))
    return free_cells_list


def cell_index(grid: Grid) -> dict[Coord, int]:
    free_cells_list = free_cells(grid)
    free_cell_pos = {}
    for i, cell in enumerate(free_cells_list):
        free_cell_pos[cell] = i
    return free_cell_pos
