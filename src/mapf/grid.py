"""Grid maps and scenarios (MAPF benchmark .map / .scen files).

The file parsing in this module is filled in. The graph functions
(neighbours, free-cell indexing) are ours to write.

Coordinates are (row, col) = (y, x). The .scen files store (x, y), and the
loader converts them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import numpy as np

Coord: TypeAlias = tuple[int, int]
Config: TypeAlias = list[Coord]
Solution: TypeAlias = list[Config]

# Characters that are passable in the MAPF benchmark maps. Everything else
# ('@', 'T', 'O', 'W') is an obstacle.
PASSABLE_CHARS = frozenset(".GS")


@dataclass(frozen=True)
class Grid:
    """A 4-connected grid: the graph G in the input of Algorithm 1.

    free[row, col] is True when the cell can hold an agent.
    """

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
    """One MAPF problem: the full input of Algorithm 1 (G, starts, goals).

    starts[i] and goals[i] belong to agent i.
    """

    grid: Grid
    starts: Config
    goals: Config
    name: str = ""

    @property
    def num_agents(self) -> int:
        return len(self.starts)


# ---------------------------------------------------------------------------
# File I/O (filled in)
# ---------------------------------------------------------------------------


def parse_map(text: str, name: str = "") -> Grid:
    """Build a Grid from text. Input of Algorithm 1 (graph G).

    Accepts the benchmark format (a header "type/height/width/map" followed by
    the rows) and also bare rows with no header, which the tests use:

        parse_map("...\\n.@.\\n...")
    """
    lines = [ln.rstrip("\r") for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() != ""]
    height = width = None
    if any(ln.strip() == "map" for ln in lines):
        split = next(i for i, ln in enumerate(lines) if ln.strip() == "map")
        for ln in lines[:split]:
            fields = ln.split()
            if len(fields) == 2 and fields[0] == "height":
                height = int(fields[1])
            elif len(fields) == 2 and fields[0] == "width":
                width = int(fields[1])
        rows = lines[split + 1 :]
    else:
        rows = lines
    if not rows:
        raise ValueError(f"map {name!r} has no rows")
    if height is None:
        height = len(rows)
    if width is None:
        width = len(rows[0])
    if len(rows) != height:
        raise ValueError(f"map {name!r}: header says {height} rows, found {len(rows)}")
    free = np.zeros((height, width), dtype=bool)
    for r, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"map {name!r}: row {r} has {len(row)} cells, expected {width}")
        for c, ch in enumerate(row):
            free[r, c] = ch in PASSABLE_CHARS
    free.setflags(write=False)
    return Grid(free=free, name=name)


def load_map(path: str | Path) -> Grid:
    """Read a benchmark .map file. Input of Algorithm 1 (graph G)."""
    path = Path(path)
    return parse_map(path.read_text(), name=path.stem)


def load_scen(path: str | Path, num_agents: int | None = None) -> tuple[Config, Config]:
    """Read a benchmark .scen file. Input of Algorithm 1 (starts s_i, goals g_i).

    Each data line is: bucket, map, width, height, start_x, start_y, goal_x,
    goal_y, optimal_length (tab separated). The first num_agents lines are
    used, which is the benchmark's convention. Returns (starts, goals) as
    (row, col) pairs.
    """
    starts: Config = []
    goals: Config = []
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if len(fields) != 9:
            continue  # the "version 1" header or a blank line
        sx, sy, gx, gy = (int(v) for v in fields[4:8])
        starts.append((sy, sx))
        goals.append((gy, gx))
        if num_agents is not None and len(starts) >= num_agents:
            break
    if num_agents is not None and len(starts) < num_agents:
        raise ValueError(f"{path}: asked for {num_agents} agents, file has {len(starts)}")
    return starts, goals


def load_instance(
    map_path: str | Path, scen_path: str | Path, num_agents: int | None = None
) -> Instance:
    """Read a map and a scenario together. Input of Algorithm 1."""
    grid = load_map(map_path)
    starts, goals = load_scen(scen_path, num_agents)
    name = f"{Path(scen_path).stem}|agents={len(starts)}"
    return Instance(grid=grid, starts=starts, goals=goals, name=name)


# ---------------------------------------------------------------------------
# Graph functions (ours to write)
# ---------------------------------------------------------------------------


def is_free(grid: Grid, cell: Coord) -> bool:
    """True when cell is inside the grid and not an obstacle.

    Algorithm 1: helper for Neigh() at Line 9.
    """
    # TODO(Person A)
    raise NotImplementedError


def neighbours(grid: Grid, cell: Coord) -> list[Coord]:
    """The free cells 4-adjacent to cell (up, down, left, right), without cell itself.

    Algorithm 1 Line 9: this is Neigh(pi_i[t]). The caller adds the "stay"
    cell. Return them in one fixed order so that runs are reproducible.
    """
    # TODO(Person A)
    raise NotImplementedError


def free_cells(grid: Grid) -> list[Coord]:
    """All free cells in row-major order: the vertex set V of graph G.

    Algorithm 1: input (graph G). Used for |V| and for free-cell indexing.
    """
    # TODO(Person A)
    raise NotImplementedError


def cell_index(grid: Grid) -> dict[Coord, int]:
    """Map each free cell to its position in free_cells(grid).

    Algorithm 1: not a line of its own. It lets Lines 12 and 15 ("is some
    agent at v now / next step?") be answered with array lookups.
    """
    # TODO(Person A)
    raise NotImplementedError
