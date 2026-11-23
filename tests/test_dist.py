"""dist.py: BFS distance tables (Algorithm 1 Line 10)."""

from conftest import not_implemented_yet
from mapf.dist import UNREACHABLE, DistTable, bfs_distances
from mapf.grid import parse_map

pytestmark = not_implemented_yet


def test_bfs_on_corridor():
    grid = parse_map("...")
    d = bfs_distances(grid, (0, 2))
    assert d.tolist() == [[2, 1, 0]]


def test_bfs_goes_round_an_obstacle():
    grid = parse_map("...\n.@.\n...")
    d = bfs_distances(grid, (0, 0))
    assert d[2, 2] == 4
    assert d[1, 1] == UNREACHABLE  # obstacle


def test_bfs_unreachable_region():
    grid = parse_map(".@.")
    d = bfs_distances(grid, (0, 0))
    assert d[0, 0] == 0
    assert d[0, 2] == UNREACHABLE


def test_dist_table_is_per_agent(two_by_two):
    table = DistTable(two_by_two.grid, two_by_two.goals)
    # agent 0's goal is (0,1); agent 1's goal is (0,0)
    assert table.get(0, (0, 1)) == 0
    assert table.get(0, (1, 0)) == 2
    assert table.get(1, (0, 0)) == 0
    assert table.get(1, (0, 1)) == 1
