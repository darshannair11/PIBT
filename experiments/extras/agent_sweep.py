"""EXTRA. The standard benchmark protocol: add agents until the solver fails.

From the MovingAI / mapf.info benchmark description: take the agents of a
scenario file in order and add one at a time until the solver cannot solve
the instance within its limit (here: max_timestep, since PIBT never runs out
of time per step). For each (scenario, solver) this gives the largest number
of agents solved, and across scenarios a success-rate-vs-agents curve.

PIBT's success is not monotone in the number of agents (a run can fail at n
and succeed at n+1), so --patience lets the sweep continue past a failure;
the default 0 is the standard "stop at the first failure", and
max_agents_solved always means "largest n solved before the sweep stopped".

Every run is validated and measured exactly as in run_extras.py; rows go to
their own CSV (default results/sweep.csv).

Example:
    python experiments/extras/agent_sweep.py --maps random-32-32-20 \\
        --types random --scens 1 2 3 4 5 --start 10 --step 10 --solvers pypibt
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.extras.common import REPO_ROOT, SCEN_TYPES, load_tracker, make_spec, mean, scen_size  # noqa: E402
from experiments.extras.run_extras import ExtraRow, run_extra, write_extra_rows  # noqa: E402
from experiments.run_compare import SOLVERS  # noqa: E402


def sweep_one(
    run_at: Callable[[int], ExtraRow], agent_counts: list[int], patience: int = 0
) -> tuple[list[ExtraRow], int]:
    """Run run_at(n) for n in agent_counts until more than `patience`
    consecutive failures. Returns the rows and the largest n solved (0 if none).
    """
    rows: list[ExtraRow] = []
    best, misses = 0, 0
    for n in agent_counts:
        row = run_at(n)
        rows.append(row)
        if row.success:
            best, misses = n, 0
        else:
            misses += 1
            if misses > patience:
                break
    return rows, best


def summarise_sweep(results: list[tuple[str, str, str, str, int]], counts: list[int], rows: list[ExtraRow]) -> str:
    """results: (map, scen type, scen name, solver, max agents solved) per sweep."""
    lines = ["max agents solved per scenario (stop at first failure unless --patience), then success rate by n"]
    keys = sorted({(m, t, s) for m, t, _, s, _ in results})
    for map_name, scen_type, solver in keys:
        best = [b for m, t, _, s, b in results if (m, t, s) == (map_name, scen_type, solver)]
        lines.append(
            f"{map_name} {scen_type} {solver}: max agents solved mean {mean(best):.1f}, "
            f"min {min(best)}, max {max(best)} over {len(best)} scenarios"
        )
        # success rate at each n over all scenarios; a scenario whose sweep
        # stopped before n counts as a failure at n
        mine = {(r.scen_name, r.num_agents): r.success for r in rows
                if (r.map_name, r.scen_type, r.solver) == (map_name, scen_type, solver)}
        scen_names = sorted({sc for m, t, sc, s, _ in results if (m, t, s) == (map_name, scen_type, solver)})
        curve = []
        for n in counts:
            ok = sum(mine.get((sc, n), False) for sc in scen_names)
            curve.append(f"{n}:{ok}/{len(scen_names)}")
        lines.append("    " + "  ".join(curve))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20"])
    parser.add_argument("--types", nargs="+", choices=SCEN_TYPES, default=["random"])
    parser.add_argument("--scens", nargs="+", type=int, default=list(range(1, 6)))
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--step", type=int, default=1, help="agents added per round (1 = the standard protocol)")
    parser.add_argument("--max-agents", type=int, default=None, help="default: every agent in the file")
    parser.add_argument("--patience", type=int, default=0, help="failures tolerated before stopping")
    parser.add_argument("--rep", type=int, default=0, help="which seed (as in run_compare) to use")
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=list(SOLVERS))
    parser.add_argument("--max-timestep", type=int, default=1000)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "sweep.csv")
    args = parser.parse_args(argv)

    tracker = load_tracker()
    all_rows: list[ExtraRow] = []
    results = []
    all_counts: set[int] = set()
    for map_name in args.maps:
        for scen_type in args.types:
            for scen_id in args.scens:
                size = scen_size(map_name, scen_type, scen_id)
                top = min(size, args.max_agents or size)
                counts = list(range(args.start, top + 1, args.step))
                all_counts.update(counts)
                for solver in args.solvers:
                    def run_at(n, m=map_name, t=scen_type, i=scen_id, s=solver):
                        return run_extra(make_spec(m, t, i, n, args.rep), s, args.max_timestep, tracker)

                    rows, best = sweep_one(run_at, counts, args.patience)
                    all_rows += rows
                    scen_name = rows[0].scen_name if rows else f"{map_name}-{scen_type}-{scen_id}"
                    results.append((map_name, scen_type, scen_name, solver, best))
                    print(f"{scen_name} {solver}: max agents solved {best}", file=sys.stderr)
    write_extra_rows(all_rows, args.out)
    print(summarise_sweep(results, sorted(all_counts), all_rows))
    print(f"wrote {len(all_rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
