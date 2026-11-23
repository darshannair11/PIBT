"""Tests for mapf.grid."""

import pytest

from conftest import DATA_DIR
from mapf.grid import (
    cell_index,
    free_cells,
    is_free,
    load_instance,
    load_map,
    load_scen,
    neighbours,
    parse_map,
)


def test_parse_map_bare_rows():
    grid = parse_map("...\n.@.\n..T")
    assert (grid.height, grid.width) == (3, 3)
    assert grid.free[0, 0] and not grid.free[1, 1] and not grid.free[2, 2]


def test_parse_map_with_header():
    grid = parse_map("type octile\nheight 1\nwidth 3\nmap\n.@.\n")
    assert (grid.height, grid.width) == (1, 3)
    assert grid.free.tolist() == [[True, False, True]]


def test_parse_map_rejects_ragged_rows():
    with pytest.raises(ValueError):
        parse_map("...\n..")


def test_load_empty_8_8():
    grid = load_map(DATA_DIR / "maps" / "empty-8-8.map")
    assert (grid.height, grid.width) == (8, 8)
    assert grid.free.all()
    assert grid.name == "empty-8-8"


def test_load_random_32_32_20():
    grid = load_map(DATA_DIR / "maps" / "random-32-32-20.map")
    assert (grid.height, grid.width) == (32, 32)
    assert not grid.free[0, 10]  # first row is "..........@......": col 10 is blocked
    assert grid.free[0, 0]


def test_load_scen_converts_xy_to_row_col():
    # first data line:  start x=1 y=4, goal x=4 y=7  (file stores x before y)
    # second data line: start x=1 y=0, goal x=3 y=2
    starts, goals = load_scen(DATA_DIR / "scens" / "empty-8-8-random-1.scen", num_agents=2)
    assert len(starts) == len(goals) == 2
    assert (starts[0], goals[0]) == ((4, 1), (7, 4))
    assert (starts[1], goals[1]) == ((0, 1), (2, 3))


def test_load_scen_all_agents_and_too_many():
    path = DATA_DIR / "scens" / "empty-8-8-random-1.scen"
    starts, _ = load_scen(path)
    assert len(starts) == 32
    with pytest.raises(ValueError):
        load_scen(path, num_agents=33)


def test_load_instance_starts_and_goals_are_free_and_distinct():
    inst = load_instance(
        DATA_DIR / "maps" / "random-32-32-20.map",
        DATA_DIR / "scens" / "random-32-32-20-random-1.scen",
        num_agents=100,
    )
    assert inst.num_agents == 100
    assert all(inst.grid.free[c] for c in inst.starts + inst.goals)
    assert len(set(inst.starts)) == 100 and len(set(inst.goals)) == 100


def test_is_free():
    grid = parse_map(".@.")
    assert is_free(grid, (0, 0))
    assert not is_free(grid, (0, 1))  # obstacle
    assert not is_free(grid, (0, 3))  # outside
    assert not is_free(grid, (-1, 0))  # outside (must not wrap around)


def test_neighbours_open_centre_and_corner():
    grid = parse_map("...\n...\n...")
    assert set(neighbours(grid, (1, 1))) == {(0, 1), (2, 1), (1, 0), (1, 2)}
    assert set(neighbours(grid, (0, 0))) == {(0, 1), (1, 0)}
    assert (1, 1) not in neighbours(grid, (1, 1))


def test_neighbours_skip_obstacles():
    grid = parse_map("...\n.@.\n...")
    assert set(neighbours(grid, (0, 1))) == {(0, 0), (0, 2)}


def test_free_cells_and_index():
    grid = parse_map(".@\n..")
    cells = free_cells(grid)
    assert cells == [(0, 0), (1, 0), (1, 1)]
    assert cell_index(grid) == {(0, 0): 0, (1, 0): 1, (1, 1): 2}
