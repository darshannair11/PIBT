"""EXTRA. The paired comparison of run_compare.py, extended with:

    - random AND even scenario files, many scenario ids (MovingAI);
    - individual success rate (fraction of agents on their goal at the end);
    - the MAPF Tracker baseline: best known sum of costs and best lower bound
      per instance, giving SOC / best-known and SOC / tracker-LB.

Every run goes through the same solve_spec / row_from_output as the core
script, so validity, success and the core metrics are computed identically.
Results go to their own CSV (default results/extras.csv).

Tracker numbers are costs only: its runtimes come from other (mostly C++)
solvers on other machines and are never compared here.

Example:
    python experiments/extras/run_extras.py --maps empty-8-8 random-32-32-20 \\
        --types random even --scens 1 2 3 4 5 --agents 10 50 100 --reps 1
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.extras.common import (  # noqa: E402
    REPO_ROOT,
    SCEN_TYPES,
    fmt,
    individual_success_rate,
    load_tracker,
    make_spec,
    mean,
    parse_scen_name,
    scen_size,
    tracker_entry,
)
from experiments.run_compare import SOLVERS, RunRow, row_from_output, solve_spec  # noqa: E402


@dataclass
class ExtraRow(RunRow):
    """A core RunRow plus the extra columns. Empty fields mean "not available"."""

    scen_type: str = ""
    individual_success_rate: float | None = None
    tracker_lower_cost: int | None = None
    tracker_best_cost: int | None = None
    tracker_closed: bool | None = None
    soc_over_best_known: float | None = None  # only for solved runs with a tracker entry
    soc_over_tracker_lb: float | None = None


def extra_row(core: RunRow, solution, goals, tracker) -> ExtraRow:
    """Add the extra columns to a core row."""
    row = ExtraRow(**asdict(core))
    row.scen_type = parse_scen_name(core.scen_name)[1]
    row.individual_success_rate = individual_success_rate(solution, goals)
    entry = tracker_entry(tracker, core.scen_name, core.num_agents) if tracker else None
    if entry is not None:
        row.tracker_lower_cost = entry.lower_cost
        row.tracker_best_cost = entry.solution_cost
        row.tracker_closed = entry.closed
        if row.success and row.sum_of_costs is not None:
            if entry.solution_cost:
                row.soc_over_best_known = row.sum_of_costs / entry.solution_cost
            if entry.lower_cost:
                row.soc_over_tracker_lb = row.sum_of_costs / entry.lower_cost
            if entry.lower_cost is not None and row.sum_of_costs < entry.lower_cost:
                # A valid solution cannot beat a correct lower bound: either the
                # cost definitions differ or the instance was loaded differently.
                print(
                    f"WARNING {core.solver} {core.scen_name} n={core.num_agents}: "
                    f"SOC {row.sum_of_costs} < tracker lower bound {entry.lower_cost}",
                    file=sys.stderr,
                )
    return row


def run_extra(spec, solver: str, max_timestep: int, tracker) -> ExtraRow:
    out = solve_spec(spec, solver, max_timestep)
    core = row_from_output(spec, solver, out)
    return extra_row(core, out.solution, out.instance.goals, tracker)


def summarise_extras(rows: list[ExtraRow]) -> str:
    """Per (map, scenario type, agents, solver): success, mean individual success
    rate over all runs, and tracker ratios over the runs every solver solved."""
    solvers = sorted({r.solver for r in rows}, key=lambda s: SOLVERS.index(s) if s in SOLVERS else 99)
    groups = sorted({(r.map_name, r.scen_type, r.num_agents) for r in rows})
    header = (
        f"{'map':<24}{'type':<7}{'agents':>6}  {'solver':<12}{'success':>9}{'indiv':>7}"
        f"{'SOC/best':>10}{'SOC/trLB':>10}{'SOC/LB':>8}{'closed':>8}"
    )
    lines = [
        "indiv = fraction of agents on their goal at the end (all runs);",
        "SOC/best, SOC/trLB = sum of costs over the tracker's best known cost and best lower bound;",
        "SOC/LB = over the sum of BFS distances. Cost ratios use only runs every solver solved.",
    ]
    for map_name, scen_type, n in groups:
        group = [r for r in rows if (r.map_name, r.scen_type, r.num_agents) == (map_name, scen_type, n)]
        by_run: dict[tuple, dict[str, ExtraRow]] = {}
        for r in group:
            by_run.setdefault((r.scen_name, r.rep), {})[r.solver] = r
        common = [k for k, per in by_run.items() if all(s in per and per[s].success for s in solvers)]
        lines += ["", f"{map_name} {scen_type}, {n} agents: costs over {len(common)} of {len(by_run)} runs", header]
        for solver in solvers:
            mine = [r for r in group if r.solver == solver]
            if not mine:
                continue
            on_common = [by_run[k][solver] for k in common]
            closed = [r for r in on_common if r.tracker_closed]
            lines.append(
                f"{map_name:<24}{scen_type:<7}{n:>6}  {solver:<12}"
                f"{f'{sum(r.success for r in mine)}/{len(mine)}':>9}"
                + fmt(mean(r.individual_success_rate for r in mine), 7, 3)
                + fmt(mean(r.soc_over_best_known for r in on_common), 10, 3)
                + fmt(mean(r.soc_over_tracker_lb for r in on_common), 10, 3)
                + fmt(mean(r.sum_of_costs / r.soc_lower_bound for r in on_common if r.soc_lower_bound), 8, 3)
                + f"{f'{len(closed)}/{len(on_common)}':>8}"
            )
    invalid = [r for r in rows if not r.valid]
    if invalid:
        lines.insert(0, f"WARNING: {len(invalid)} invalid solutions")
    return "\n".join(lines)


def write_extra_rows(rows: list[ExtraRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[fld.name for fld in fields(ExtraRow)])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--maps", nargs="+", default=["empty-8-8", "random-32-32-20"])
    parser.add_argument("--types", nargs="+", choices=SCEN_TYPES, default=list(SCEN_TYPES))
    parser.add_argument("--scens", nargs="+", type=int, default=list(range(1, 6)), help="scenario ids (1-25)")
    parser.add_argument("--agents", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--reps", type=int, default=1, help="seeds per instance")
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=list(SOLVERS))
    parser.add_argument("--max-timestep", type=int, default=1000)
    parser.add_argument("--no-tracker", action="store_true", help="skip the tracker columns")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "extras.csv")
    args = parser.parse_args(argv)

    tracker = {} if args.no_tracker else load_tracker()
    if not tracker and not args.no_tracker:
        print("note: no tracker CSVs in data/tracker, tracker columns will be empty", file=sys.stderr)

    rows: list[ExtraRow] = []
    for map_name in args.maps:
        for scen_type in args.types:
            for scen_id in args.scens:
                size = scen_size(map_name, scen_type, scen_id)
                for n in args.agents:
                    if n > size:
                        print(f"skip {map_name}-{scen_type}-{scen_id}: only {size} agents", file=sys.stderr)
                        continue
                    for rep in range(args.reps):
                        spec = make_spec(map_name, scen_type, scen_id, n, rep)
                        for solver in args.solvers:
                            rows.append(run_extra(spec, solver, args.max_timestep, tracker))
    write_extra_rows(rows, args.out)
    print(summarise_extras(rows))
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
