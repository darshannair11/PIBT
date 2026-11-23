"""EXTRA. Pieces shared by the extra experiments: run specs over random AND
even scenarios, the individual-success metric, and the MAPF Tracker baseline.

Nothing in src/mapf or experiments/run_compare.py depends on this folder; the
core evaluation runs without it.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT / "src", REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from experiments.run_compare import RunSpec  # noqa: E402
from mapf.grid import Config, Solution  # noqa: E402
from mapf.seeds import derive_seed  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
TRACKER_DIR = DATA_DIR / "tracker"
SCEN_TYPES = ("random", "even")

_SCEN_NAME = re.compile(r"^(?P<map>.+)-(?P<type>random|even)-(?P<id>\d+)$")


# ---------------------------------------------------------------------------
# Instances
# ---------------------------------------------------------------------------


def parse_scen_name(scen_name: str) -> tuple[str, str, int]:
    """'random-32-32-20-even-7' -> ('random-32-32-20', 'even', 7).

    The map name may itself contain dashes or the word 'random', so the
    scenario type and id are taken from the end.
    """
    m = _SCEN_NAME.match(scen_name)
    if not m:
        raise ValueError(f"not a benchmark scenario name: {scen_name!r}")
    return m["map"], m["type"], int(m["id"])


def scen_path(map_name: str, scen_type: str, scen_id: int) -> Path:
    path = DATA_DIR / "scens" / f"{map_name}-{scen_type}-{scen_id}.scen"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {path}. Run: python experiments/extras/fetch_movingai.py --maps {map_name}"
        )
    return path


def make_spec(map_name: str, scen_type: str, scen_id: int, num_agents: int, rep: int) -> RunSpec:
    """A RunSpec for any scenario type, seeded exactly like run_compare.build_specs."""
    map_path = DATA_DIR / "maps" / f"{map_name}.map"
    if not map_path.is_file():
        raise FileNotFoundError(
            f"missing {map_path}. Run: python experiments/extras/fetch_movingai.py --maps {map_name}"
        )
    path = scen_path(map_name, scen_type, scen_id)
    seed = derive_seed(map_name, path.stem, num_agents, rep)
    return RunSpec(map_name, path.stem, num_agents, rep, seed, map_path, path)


def scen_size(map_name: str, scen_type: str, scen_id: int) -> int:
    """Number of agents listed in a scenario file (the largest usable instance)."""
    lines = scen_path(map_name, scen_type, scen_id).read_text().splitlines()
    return sum(1 for ln in lines if len(ln.split()) == 9)


# ---------------------------------------------------------------------------
# Extra metric: individual success rate
# ---------------------------------------------------------------------------


def individual_success_rate(solution: Solution, goals: Config) -> float:
    """Fraction of agents standing on their goal in the last configuration.

    One-shot success is all-or-nothing: a run that ends with 198 of 200 agents
    home counts the same as one that ends with none. This separates them. It
    equals 1.0 exactly when mapf.metrics.is_success is True.
    """
    if not solution or not goals:
        return math.nan
    last = solution[-1]
    return sum(tuple(u) == tuple(g) for u, g in zip(last, goals)) / len(goals)


# ---------------------------------------------------------------------------
# Baseline: MAPF Tracker (https://tracker.pathfinding.ai)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrackerEntry:
    """Best results recorded by the MAPF Tracker for one instance.

    lower_cost:    largest lower bound any submitted solver reported on the sum
                   of costs. The tracker does not verify lower bounds.
    solution_cost: smallest validated sum of costs (best known solution).
    closed:        both are known and equal, so solution_cost is optimal.
    The tracker's cost is the sum over agents of the time of final arrival at
    the goal, the same definition as mapf.metrics.sum_of_costs.
    """

    lower_cost: int | None
    solution_cost: int | None

    @property
    def closed(self) -> bool:
        return self.lower_cost is not None and self.lower_cost == self.solution_cost


TrackerKey = tuple[str, str, int, int]  # (map, scen type, scen id, agents)


def _int_or_none(text: str | None) -> int | None:
    text = (text or "").strip()
    return int(float(text)) if text else None


def load_tracker(folder: Path = TRACKER_DIR) -> dict[TrackerKey, TrackerEntry]:
    """Read every tracker results CSV in folder (as produced by its bulk export).

    Columns: map_name, scen_type, type_id, agents, lower_cost, solution_cost.
    type_id is the same number as in the MovingAI file name (checked on
    empty-8-8-random-1: lower_cost for 2 agents is 10, the sum of their
    Manhattan distances).
    """
    table: dict[TrackerKey, TrackerEntry] = {}
    for path in sorted(folder.glob("*.csv")):
        with path.open(newline="") as f:
            for rec in csv.DictReader(f):
                agents = rec.get("agents") or rec.get("agent_count")
                key = (rec["map_name"], rec["scen_type"], int(rec["type_id"]), int(agents))
                table[key] = TrackerEntry(
                    _int_or_none(rec.get("lower_cost")), _int_or_none(rec.get("solution_cost"))
                )
    return table


def tracker_entry(
    table: dict[TrackerKey, TrackerEntry], scen_name: str, num_agents: int
) -> TrackerEntry | None:
    map_name, scen_type, scen_id = parse_scen_name(scen_name)
    return table.get((map_name, scen_type, scen_id, num_agents))


def mean(values) -> float:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(vals) / len(vals) if vals else math.nan


def fmt(value: float, width: int, digits: int) -> str:
    return f"{'-':>{width}}" if value is None or math.isnan(value) else f"{value:>{width}.{digits}f}"
