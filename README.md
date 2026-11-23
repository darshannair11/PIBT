# PIBT with improvements (CS279, Fall 2026, project 4)

Darshan Nair and Suyash. One-shot multi-agent path finding on 4-connected
grids, with our own Python implementation of Priority Inheritance with
Backtracking (PIBT) and simplified re-implementations of published variants.

Reference: Okumura, Machida, Défago, Tamura, "Priority Inheritance with
Backtracking for Iterative Multi-agent Path Finding", arXiv 1901.11282v5,
Algorithm 1.

Project decisions, the professor's comment and the work split are in
[PROJECT_NOTES.md](PROJECT_NOTES.md).

## Status

Done: the file loader, the seed helper, the pypibt wrapper, the test
fixtures, and the evaluation side: `validate.py`, `metrics.py`, and
`run_one` / `summarise` in `experiments/run_compare.py` (checked against
pypibt's output). Still stubs, raising `NotImplementedError` and marked
`TODO(Darshan)`: the graph functions in `grid.py`, `dist.py` and the PIBT core
in `pibt.py`. Until `DistTable` exists, `run_compare.py` cannot compute lower
bounds, so it does not run yet.

Optional extra evaluation (more scenarios, MAPF Tracker baseline,
add-agents-until-failure sweep) is in `experiments/extras/`.

## Setup

Python 3.10 or newer, with numpy.

```bash
git submodule update --init
```

```bash
pip install -e ".[dev]"
```

```bash
pytest
```

On the skeleton, the loader and import tests pass and the rest show as
`xfailed`. As a stub is implemented its tests turn into `xpassed`; a test
whose code runs but gives a wrong answer fails normally. Once every test in a
file passes, delete the `not_implemented_yet` marker from that file.

## Layout

| Path | Contents |
|---|---|
| `src/mapf/grid.py` | `.map` / `.scen` loader (done), neighbours, free-cell indexing |
| `src/mapf/dist.py` | BFS distance tables from each goal |
| `src/mapf/pibt.py` | `PIBT` class: Algorithm 1, with hooks `order_candidates` and `plan_step` |
| `src/mapf/validate.py` | solution checker: starts, goals, legal moves, vertex and swap conflicts |
| `src/mapf/metrics.py` | success, sum of costs, makespan, runtime per step, recursion depth, goal displacements |
| `src/mapf/seeds.py` | `derive_seed`, the only source of seeds (done) |
| `experiments/crosscheck.py` | wrapper that runs pypibt (done) |
| `experiments/run_compare.py` | paired runs of our PIBT and pypibt, CSV output |
| `experiments/extras/` | optional extra evaluation: more scenarios, MAPF Tracker baseline, add-agents-until-failure sweep ([README](experiments/extras/README.md)) |
| `tests/` | hand-made instances: corridor swap, 2x2 grid, dead end, agent already on its goal |
| `data/` | benchmark maps and scenarios |
| `third_party/pypibt` | git submodule, used only by `experiments/crosscheck.py` |

Coordinates are `(row, col)` everywhere. A solution is a list of
configurations, `solution[t][i]` being agent `i`'s cell at timestep `t`.

## Running

pypibt alone, as a reference:

```bash
python experiments/crosscheck.py -m data/maps/random-32-32-20.map -i data/scens/random-32-32-20-random-1.scen -N 100 -s 0
```

The planned paired runs and their seeds:

```bash
python experiments/run_compare.py --list
```

## Data

`data/maps` and `data/scens` hold `empty-8-8` and `random-32-32-20` with
their `random-1` scenario, from the MAPF benchmark set
(<https://movingai.com/benchmarks/mapf/index.html>; Stern et al., "Multi-Agent
Pathfinding: Definitions, Variants, and Benchmarks", SoCS 2019). Still to add:
warehouse-20-40-10-2-2, den520d, ost003d, Paris_1_256, and more scenario
files (the runner expects `data/scens/<map>-random-<id>.scen`).

## Third-party code

`third_party/pypibt` is <https://github.com/Kei18/pypibt> (MIT licence,
copyright Keisuke Okumura), pinned as a submodule with its `LICENCE.txt`. It
is a cross-check target only; none of its code is copied into `src/`. It
differs from the paper: its tie-break is random only, and its initial
priorities are start-to-goal distance divided by grid size.
