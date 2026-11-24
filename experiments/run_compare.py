"""Run our PIBT and pypibt on the same paired instances and write one CSV row per run.

A run is identified by (map, scenario, number of agents, repetition). Both
solvers get the same instance and the same seed, derived with
mapf.seeds.derive_seed (zlib.crc32), never with hash().

Rules this script must keep:
    - every returned solution goes through mapf.validate, ours and pypibt's;
    - costs are compared only on instances that both solvers solved;
    - runtime is comparable only between Python implementations.

The argument parsing, instance enumeration, seeding and CSV writing are
filled in. run_one and summarise are ours.

Example:
    python experiments/run_compare.py --maps empty-8-8 random-32-32-20 \\
        --agents 10 20 --reps 3 --out results/first.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:  # lets the script run without "pip install -e ."
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mapf.seeds import derive_seed  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
S1 = {"hindrance": True}
S2 = {"weighted_choice": True}
S3 = {"swap_on_failed_push": True}
S4 = {"protect_parked": 0.8}
S5 = {"goal_lookahead": 6}
RANDOM = {"tie_break": "random"}
OUR_VARIANTS = {
    "ours-paper": {"tie_break": "paper"},
    "ours-random": RANDOM,
    "s1-hindrance": RANDOM | S1,
    "s2-weighted": RANDOM | S2,
    "s3-swap": RANDOM | S3,
    "s4-parked": RANDOM | S4,
    "s5-lookahead": RANDOM | S5,
    "s1+s3": RANDOM | S1 | S3,
    "s1+s3+s4": RANDOM | S1 | S3 | S4,
    "s2+s3": RANDOM | S2 | S3,
    "s2+s3+s5": RANDOM | S2 | S3 | S5,
}
SOLVERS = (*OUR_VARIANTS, "pypibt")
DEFAULT_SOLVERS = ("ours-paper", "ours-random", "pypibt")


@dataclass(frozen=True)
class RunSpec:
    """One paired run: the same instance and seed for every solver."""

    map_name: str
    scen_name: str
    num_agents: int
    rep: int
    seed: int
    map_path: Path
    scen_path: Path


@dataclass
class RunRow:
    """One CSV row: one solver on one RunSpec. Empty fields mean "not solved"."""

    map_name: str
    scen_name: str
    num_agents: int
    rep: int
    seed: int
    solver: str
    success: bool = False
    valid: bool = False
    sum_of_costs: int | None = None
    makespan: int | None = None
    soc_lower_bound: int | None = None
    makespan_lower_bound: int | None = None
    runtime_per_step_s: float | None = None
    avg_recursion_depth: float | None = None
    goal_displacements: int | None = None


def scen_files_for(map_name: str, scen_ids: list[int]) -> list[Path]:
    """Paths of data/scens/<map>-random-<id>.scen for the requested ids."""
    paths = [DATA_DIR / "scens" / f"{map_name}-random-{i}.scen" for i in scen_ids]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("missing scenario files: " + ", ".join(str(p) for p in missing))
    return paths


def build_specs(
    maps: list[str], scen_ids: list[int], agents: list[int], reps: int
) -> list[RunSpec]:
    """Every (map, scenario, agents, rep) combination, each with its own seed."""
    specs: list[RunSpec] = []
    for map_name in maps:
        map_path = DATA_DIR / "maps" / f"{map_name}.map"
        if not map_path.is_file():
            raise FileNotFoundError(f"missing map file: {map_path}")
        for scen_path in scen_files_for(map_name, scen_ids):
            for n in agents:
                for rep in range(reps):
                    seed = derive_seed(map_name, scen_path.stem, n, rep)
                    specs.append(
                        RunSpec(map_name, scen_path.stem, n, rep, seed, map_path, scen_path)
                    )
    return specs


def write_rows(rows: list[RunRow], out_path: Path) -> None:
    """Write the rows as CSV, creating the output folder if needed."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[fld.name for fld in fields(RunRow)])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


# ---------------------------------------------------------------------------
# Ours to write
# ---------------------------------------------------------------------------


@dataclass
class SolverOutput:
    """What one solver produced on one spec, before any metric is computed."""

    instance: object  # mapf.grid.Instance, loaded by our own loader
    solution: list  # solution[t][i] = agent i's cell at t
    dist: object  # mapf.dist.DistTable for the lower bounds
    runtime_per_step_s: float
    avg_recursion_depth: float | None  # None for pypibt (no per-step counters)


def solve_spec(spec: RunSpec, solver: str, max_timestep: int) -> SolverOutput:
    """Run one solver on one spec and return its raw output (no metrics yet).

    Split out of run_one so that experiments/extras can reuse the same run
    without solving twice.
    """
    from mapf.dist import DistTable
    from mapf.grid import load_instance
    from mapf.metrics import avg_recursion_depth, runtime_per_step

    inst = load_instance(spec.map_path, spec.scen_path, spec.num_agents)
    if solver in OUR_VARIANTS:
        from mapf.pibt import PIBT

        pibt = PIBT(inst.grid, inst.starts, inst.goals, seed=spec.seed, **OUR_VARIANTS[solver])
        solution = pibt.solve(max_timestep=max_timestep)
        dist = pibt.dist if pibt.dist is not None else DistTable(inst.grid, inst.goals)
        return SolverOutput(
            inst, solution, dist, runtime_per_step(pibt.stats), avg_recursion_depth(pibt.stats)
        )
    if solver == "pypibt":
        from experiments.crosscheck import run_pypibt

        result = run_pypibt(spec.map_path, spec.scen_path, spec.num_agents, spec.seed, max_timestep)
        return SolverOutput(
            inst,
            result.solution,
            DistTable(inst.grid, inst.goals),
            result.runtime_s / max(result.num_steps, 1),
            None,
        )
    raise ValueError(f"unknown solver {solver!r}; expected one of {SOLVERS}")


def row_from_output(spec: RunSpec, solver: str, out: SolverOutput) -> RunRow:
    """Validate a SolverOutput and turn it into a RunRow (see run_one for the rules)."""
    from mapf.metrics import (
        goal_displacements,
        is_success,
        makespan,
        makespan_lower_bound,
        sum_of_costs,
        sum_of_costs_lower_bound,
    )
    from mapf.validate import validate_solution

    inst = out.instance
    row = RunRow(spec.map_name, spec.scen_name, spec.num_agents, spec.rep, spec.seed, solver)
    row.runtime_per_step_s = out.runtime_per_step_s
    row.avg_recursion_depth = out.avg_recursion_depth

    # Our own validator decides validity for every solver. pypibt's own flag
    # (valid_by_pypibt) is False whenever the goals are not reached, so it
    # mixes legality with success and is not used here.
    check = validate_solution(inst.grid, inst.starts, inst.goals, out.solution, require_goals=False)
    row.valid = check.ok
    if not check.ok:
        print(f"INVALID {solver} on {spec}: {check.errors[:3]}", file=sys.stderr)
    row.success = row.valid and is_success(out.solution, inst.goals)

    row.soc_lower_bound = sum_of_costs_lower_bound(out.dist, inst.starts)
    row.makespan_lower_bound = makespan_lower_bound(out.dist, inst.starts)
    row.goal_displacements = goal_displacements(out.solution, inst.goals)
    if row.success:
        row.sum_of_costs = sum_of_costs(out.solution, inst.goals)
        row.makespan = makespan(out.solution)
    return row


def run_one(spec: RunSpec, solver: str, max_timestep: int) -> RunRow:
    """Run one solver on one spec and fill a RunRow.

    Runs Algorithm 1 to termination, then measures it:
        "ours-paper" / "ours-random": mapf.pibt.PIBT with that tie_break;
        "pypibt": experiments.crosscheck.run_pypibt.
    For every solver: validate with mapf.validate (require_goals=False), set
    valid and success, and fill the cost fields only when success is True.
    pypibt has no per-step counters, so its recursion depth stays empty.

    Choices made here:
        - success means valid AND on the goals: an illegal solution never counts;
        - the lower bounds are properties of the instance, so they are filled
          for every row, solved or not, from our own DistTable;
        - runtime_per_step_s and goal_displacements describe the run, not its
          cost, so they are filled for unsolved runs too;
        - pypibt's runtime includes its lazily built distance tables (they
          cannot be separated from its steps); ours excludes the BFS tables,
          which are built in reset() before the first step is timed.
    """
    return row_from_output(spec, solver, solve_spec(spec, solver, max_timestep))


def _mean(values: list[float]) -> float:
    values = [v for v in values if v is not None and not math.isnan(v)]
    return sum(values) / len(values) if values else math.nan


def _fmt(value: float, width: int, digits: int) -> str:
    """Right-aligned number, or "-" when there is nothing to show (nan)."""
    return f"{'-':>{width}}" if math.isnan(value) else f"{value:>{width}.{digits}f}"


def summarise(rows: list[RunRow]) -> str:
    """Text summary per (map, agents, solver): success rate and mean cost ratios.

    Not part of Algorithm 1. Cost ratios must use only the runs that every
    solver being compared solved; say how many runs that was.

    The ratios are means over the common runs of SOC / SOC lower bound and
    makespan / makespan lower bound (1.0 would be optimal on that bound).
    """
    solvers = sorted({r.solver for r in rows}, key=lambda s: SOLVERS.index(s) if s in SOLVERS else 99)
    groups = sorted({(r.map_name, r.num_agents) for r in rows})
    lines = []
    invalid = [r for r in rows if not r.valid]
    if invalid:
        lines.append(f"WARNING: {len(invalid)} invalid solutions (illegal moves or conflicts):")
        for r in invalid[:10]:
            lines.append(f"  {r.solver} {r.map_name} {r.scen_name} agents={r.num_agents} rep={r.rep}")
    header = f"{'map':<18}{'agents':>7}  {'solver':<12}{'success':>10}{'SOC/LB':>9}{'MS/LB':>8}{'ms/step':>9}{'depth':>7}{'displ':>7}"
    for map_name, n in groups:
        in_group = [r for r in rows if r.map_name == map_name and r.num_agents == n]
        by_run: dict[tuple, dict[str, RunRow]] = {}
        for r in in_group:
            by_run.setdefault((r.scen_name, r.rep), {})[r.solver] = r
        common = [k for k, per in by_run.items() if all(s in per and per[s].success for s in solvers)]
        lines.append("")
        lines.append(f"{map_name}, {n} agents: costs over the {len(common)} of {len(by_run)} runs solved by every solver")
        lines.append(header)
        for solver in solvers:
            mine = [r for r in in_group if r.solver == solver]
            if not mine:
                continue
            solved = sum(r.success for r in mine)
            on_common = [by_run[k][solver] for k in common]
            soc = _mean([r.sum_of_costs / r.soc_lower_bound for r in on_common if r.soc_lower_bound])
            ms = _mean([r.makespan / r.makespan_lower_bound for r in on_common if r.makespan_lower_bound])
            lines.append(
                f"{map_name:<18}{n:>7}  {solver:<12}{f'{solved}/{len(mine)}':>10}"
                + _fmt(soc, 9, 3)
                + _fmt(ms, 8, 3)
                + _fmt(1000 * _mean([r.runtime_per_step_s for r in mine]), 9, 2)
                + _fmt(_mean([r.avg_recursion_depth for r in mine]), 7, 2)
                + _fmt(_mean([r.goal_displacements for r in mine]), 7, 1)
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--maps", nargs="+", default=["empty-8-8", "random-32-32-20"])
    parser.add_argument("--scens", nargs="+", type=int, default=[1], help="scenario ids")
    parser.add_argument("--agents", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--reps", type=int, default=3, help="repetitions (seeds) per instance")
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=list(DEFAULT_SOLVERS))
    parser.add_argument("--max-timestep", type=int, default=1000)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "compare.csv")
    parser.add_argument("--list", action="store_true", help="print the planned runs and exit")
    args = parser.parse_args(argv)

    specs = build_specs(args.maps, args.scens, args.agents, args.reps)
    if args.list:
        for s in specs:
            print(f"{s.map_name}\t{s.scen_name}\tagents={s.num_agents}\trep={s.rep}\tseed={s.seed}")
        print(f"{len(specs)} instances x {len(args.solvers)} solvers")
        return 0

    rows = [run_one(spec, solver, args.max_timestep) for spec in specs for solver in args.solvers]
    write_rows(rows, args.out)
    print(summarise(rows))
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
