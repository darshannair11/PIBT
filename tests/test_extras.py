"""experiments/extras: tracker baseline, individual success rate, sweep, summary.

These cover the EXTRA evaluation only; the core tests do not depend on them.
"""

import math

import pytest

from conftest import DATA_DIR
from experiments.extras.agent_sweep import sweep_one
from experiments.extras.common import (
    TrackerEntry,
    individual_success_rate,
    load_tracker,
    parse_scen_name,
    tracker_entry,
)
from experiments.extras.run_extras import ExtraRow, extra_row, summarise_extras
from experiments.run_compare import RunRow
from mapf.grid import load_scen

TRACKER_DIR = DATA_DIR / "tracker"
needs_tracker = pytest.mark.skipif(
    not (TRACKER_DIR / "empty-8-8-random-1.csv").is_file(), reason="tracker export not in data/tracker"
)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("random-32-32-20-random-1", ("random-32-32-20", "random", 1)),
        ("random-32-32-20-even-25", ("random-32-32-20", "even", 25)),
        ("warehouse-20-40-10-2-2-random-3", ("warehouse-20-40-10-2-2", "random", 3)),
        ("Paris_1_256-even-12", ("Paris_1_256", "even", 12)),
    ],
)
def test_parse_scen_name(name, expected):
    assert parse_scen_name(name) == expected


def test_individual_success_rate(two_by_two, two_by_two_solution):
    assert individual_success_rate(two_by_two_solution, two_by_two.goals) == 1.0
    # t=1: a0 is on (0,1) = its goal, a1 is not
    assert individual_success_rate(two_by_two_solution[:2], two_by_two.goals) == 0.5
    assert math.isnan(individual_success_rate([], two_by_two.goals))


@needs_tracker
def test_tracker_ids_and_costs_match_our_scenario_files():
    """type_id is the MovingAI file number, and the tracker's cost is ours:
    with 1-2 agents on an empty map the optimum is the sum of Manhattan distances."""
    table = load_tracker(TRACKER_DIR)
    starts, goals = load_scen(DATA_DIR / "scens" / "empty-8-8-random-1.scen", 2)
    manhattan = [abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(starts, goals)]
    assert tracker_entry(table, "empty-8-8-random-1", 1) == TrackerEntry(manhattan[0], manhattan[0])
    assert tracker_entry(table, "empty-8-8-random-1", 2).solution_cost == sum(manhattan)
    assert tracker_entry(table, "empty-8-8-random-1", 1).closed


def _core(success, soc=None, solver="pypibt", rep=0, scen="empty-8-8-random-1", n=2):
    return RunRow("empty-8-8", scen, n, rep, 0, solver, success=success, valid=True,
                  sum_of_costs=soc, makespan=soc and 5, soc_lower_bound=10, makespan_lower_bound=5)


def test_extra_row_tracker_ratios():
    table = {("empty-8-8", "random", 1, 2): TrackerEntry(lower_cost=10, solution_cost=12)}
    goals = [(0, 0), (1, 1)]
    row = extra_row(_core(True, 15), [[(0, 0), (1, 1)]], goals, table)
    assert row.scen_type == "random" and row.individual_success_rate == 1.0
    assert row.soc_over_best_known == pytest.approx(15 / 12)
    assert row.soc_over_tracker_lb == pytest.approx(15 / 10)
    assert row.tracker_closed is False
    # unsolved: tracker numbers are recorded, ratios stay empty
    unsolved = extra_row(_core(False), [[(0, 0), (2, 2)]], goals, table)
    assert unsolved.tracker_best_cost == 12 and unsolved.soc_over_best_known is None
    assert unsolved.individual_success_rate == 0.5


def test_summarise_extras_uses_common_runs():
    table = {("empty-8-8", "random", 1, 2): TrackerEntry(10, 10)}
    goals = [(0, 0), (1, 1)]
    rows = [
        extra_row(_core(True, 10, "ours-paper", 0), [goals], goals, table),
        extra_row(_core(True, 20, "pypibt", 0), [goals], goals, table),
        extra_row(_core(True, 50, "ours-paper", 1), [goals], goals, table),  # pypibt failed rep 1
        extra_row(_core(False, None, "pypibt", 1), [[(0, 0), (3, 3)]], goals, table),
    ]
    text = summarise_extras(rows)
    assert "costs over 1 of 2 runs" in text
    ours = next(ln for ln in text.splitlines() if "ours-paper" in ln)
    assert "1.000" in ours and "5.000" not in ours


def test_sweep_stops_at_first_failure_and_reports_last_success():
    outcome = {10: True, 20: True, 30: False, 40: True}
    run_at = lambda n: ExtraRow("m", "m-random-1", n, 0, 0, "x", success=outcome[n])  # noqa: E731
    rows, best = sweep_one(run_at, [10, 20, 30, 40])
    assert best == 20 and [r.num_agents for r in rows] == [10, 20, 30]
    rows, best = sweep_one(run_at, [10, 20, 30, 40], patience=1)
    assert best == 40 and len(rows) == 4
