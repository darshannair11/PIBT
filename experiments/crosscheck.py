"""Thin wrapper around pypibt (third_party/pypibt, MIT licence, Keisuke Okumura).

This is the only file that imports pypibt. Nothing from pypibt is copied into
src/. pypibt is the cross-check target, not our implementation.

How pypibt differs from the paper's Algorithm 1 (and so from our Base PIBT):
    - Line 10 tie-break is random only (no "cells without agents first");
    - Line 2 initial priorities are dist(start, goal) / grid size, not an
      arbitrary distinct epsilon_i;
    - it always takes at least one step, even when starts == goals.
Compare it with our tie_break="random" variant, and expect the same success
pattern and similar costs, not identical paths.

Run directly for a quick look:
    python experiments/crosscheck.py -m data/maps/random-32-32-20.map \\
        -i data/scens/random-32-32-20-random-1.scen -N 100 -s 0
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPIBT_SRC = REPO_ROOT / "third_party" / "pypibt" / "src"


@dataclass
class PypibtResult:
    """What one pypibt run produced. Not part of Algorithm 1."""

    solution: list  # list of configurations; each is a list of (row, col)
    reached_goals: bool  # last configuration equals the goals
    valid_by_pypibt: bool  # pypibt's own checker (ours must be run as well)
    runtime_s: float  # whole run, including pypibt's distance tables
    num_steps: int  # len(solution) - 1


def _import_pypibt():
    """Import pypibt from the submodule. Not part of Algorithm 1."""
    if not (PYPIBT_SRC / "pypibt").is_dir():
        raise RuntimeError(
            "third_party/pypibt is empty. Run: git submodule update --init"
        )
    if str(PYPIBT_SRC) not in sys.path:
        sys.path.insert(0, str(PYPIBT_SRC))
    import pypibt

    return pypibt


def run_pypibt(
    map_path: str | Path,
    scen_path: str | Path,
    num_agents: int,
    seed: int,
    max_timestep: int = 1000,
) -> PypibtResult:
    """Solve one instance with pypibt, using pypibt's own loaders.

    Runs pypibt's version of Algorithm 1 from start to finish. pypibt uses
    (row, col) coordinates, the same as mapf.grid, so the solution can be
    passed to mapf.validate and mapf.metrics unchanged.
    """
    pypibt = _import_pypibt()
    grid = pypibt.get_grid(str(map_path))
    starts, goals = pypibt.get_scenario(str(scen_path), num_agents)
    if len(starts) < num_agents:
        raise ValueError(f"{scen_path}: asked for {num_agents} agents, file has {len(starts)}")

    t0 = time.perf_counter()
    solver = pypibt.PIBT(grid, starts, goals, seed=seed)
    plan = solver.run(max_timestep=max_timestep)
    runtime_s = time.perf_counter() - t0

    solution = [[(int(r), int(c)) for (r, c) in config] for config in plan]
    return PypibtResult(
        solution=solution,
        reached_goals=solution[-1] == [tuple(g) for g in goals],
        valid_by_pypibt=bool(pypibt.is_valid_mapf_solution(grid, starts, goals, plan)),
        runtime_s=runtime_s,
        num_steps=len(solution) - 1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pypibt on one instance.")
    parser.add_argument("-m", "--map-file", required=True)
    parser.add_argument("-i", "--scen-file", required=True)
    parser.add_argument("-N", "--num-agents", type=int, required=True)
    parser.add_argument("-s", "--seed", type=int, default=0)
    parser.add_argument("--max-timestep", type=int, default=1000)
    args = parser.parse_args(argv)

    result = run_pypibt(
        args.map_file, args.scen_file, args.num_agents, args.seed, args.max_timestep
    )
    per_step_ms = 1000 * result.runtime_s / max(result.num_steps, 1)
    print(f"reached goals:   {result.reached_goals}")
    print(f"valid (pypibt):  {result.valid_by_pypibt}")
    print(f"steps:           {result.num_steps}")
    print(f"runtime:         {result.runtime_s:.3f} s ({per_step_ms:.2f} ms per step)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
