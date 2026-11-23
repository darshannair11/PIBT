"""Run our PIBT and pypibt on the same paired instances and write one CSV row per run.

A run is identified by (map, scenario, number of agents, repetition). Both
solvers get the same instance and the same seed, derived with
mapf.seeds.derive_seed (zlib.crc32), never with hash().

Rules this script must keep (see CLAUDE.md):
    - every returned solution goes through mapf.validate, ours and pypibt's;
    - costs are compared only on instances that both solvers solved;
    - runtime is comparable only between Python implementations.

The argument parsing, instance enumeration, seeding and CSV writing are
filled in. The two functions marked TODO are ours to write.

Example:
    python experiments/run_compare.py --maps empty-8-8 random-32-32-20 \\
        --agents 10 20 --reps 3 --out results/first.csv
"""

from __future__ import annotations

import argparse
import csv
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
SOLVERS = ("ours-paper", "ours-random", "pypibt")


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


def run_one(spec: RunSpec, solver: str, max_timestep: int) -> RunRow:
    """Run one solver on one spec and fill a RunRow.

    Runs Algorithm 1 to termination, then measures it:
        "ours-paper" / "ours-random": mapf.pibt.PIBT with that tie_break;
        "pypibt": experiments.crosscheck.run_pypibt.
    For every solver: validate with mapf.validate (require_goals=False), set
    valid and success, and fill the cost fields only when success is True.
    pypibt has no per-step counters, so its recursion depth stays empty.
    """
    # TODO(Person A)
    raise NotImplementedError


def summarise(rows: list[RunRow]) -> str:
    """Text summary per (map, agents, solver): success rate and mean cost ratios.

    Not part of Algorithm 1. Cost ratios must use only the runs that every
    solver being compared solved; say how many runs that was.
    """
    # TODO(Person A)
    raise NotImplementedError


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--maps", nargs="+", default=["empty-8-8", "random-32-32-20"])
    parser.add_argument("--scens", nargs="+", type=int, default=[1], help="scenario ids")
    parser.add_argument("--agents", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--reps", type=int, default=3, help="repetitions (seeds) per instance")
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=list(SOLVERS))
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
