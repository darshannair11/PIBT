# Project context for Claude sessions

CS279 Fall 2026 project 4, Darshan and Suyash: "Priority Inheritance with
Backtracking (PIBT) with Improvements". Research-oriented, Python. Report due
Nov 23, 2026; updates allowed until Dec 7, 2026. Read `PROJECT_NOTES.md` first:
it holds the professor's comment, the decisions, the related-work table and
the work split.

## The rule that matters most

Darshan and Suyash write the algorithms themselves; that is the point of the
project. Do not fill in bodies marked `TODO` in `src/mapf/` (PIBT, BFS,
neighbours, validator, metrics) or in `experiments/run_compare.py` unless
asked to in that session. Boilerplate (argument parsing, file I/O, test
fixtures) is fine. Never copy code from `third_party/pypibt` into `src/`. If
something is ambiguous, ask instead of guessing.

## Problem

- One-shot MAPF on 4-connected grids. No lifelong MAPF.
- Vertex conflicts and swap conflicts are forbidden.
- Reference: Okumura et al., arXiv 1901.11282v5, Algorithm 1 (22 numbered
  lines; they are reproduced at the top of `src/mapf/pibt.py`).

## Base PIBT (the paper's version)

- Priority `p_i`: set to a unique tie-breaker `epsilon_i` in [0, 1) at the
  start (Line 2); each timestep, reset to `epsilon_i` if the agent is on its
  goal, otherwise add 1 (Line 3).
- Procedure `PIBT(a_i, a_j)` (Lines 8-22): candidates are the neighbours plus
  staying; sort by distance to goal, ties broken by preferring cells with no
  agent, then random (Line 10 and Appendix B); skip cells already claimed this
  step (Line 12) and the caller's cell (Line 13); reserve (Line 14); if an
  undecided agent is on the chosen cell it inherits priority and we recurse
  (Lines 15-16); if that fails, try the next candidate; if nothing works, stay
  and return invalid (Lines 20-21).
- Second reference variant: pure random ties (`tie_break="random"`), kept
  because the tie-break rule changes results.

## pypibt (cross-check target)

- `third_party/pypibt`, a git submodule of github.com/Kei18/pypibt, MIT, with
  its `LICENCE.txt`. Used only by `experiments/crosscheck.py`.
- Differs from the paper: random-only tie-break; initial priorities are
  dist(start, goal) / grid size; always takes at least one step.
- It declares Python 3.11+, but runs on 3.10 when imported from its `src`
  folder, which is what the wrapper does.

## Layout

- `src/mapf/grid.py`: `.map`/`.scen` loader, neighbours, free-cell indexing
- `src/mapf/dist.py`: BFS distance tables from each goal
- `src/mapf/pibt.py`: `PIBT` class; hooks `order_candidates(agent, candidates,
  state)` (tie-breaking, guidance) and `plan_step(state)` (lookahead)
- `src/mapf/validate.py`: start/goal match, legal moves, vertex and swap conflicts
- `src/mapf/metrics.py`: success, sum of costs, makespan, runtime per step,
  average recursion depth, goal displacement count
- `src/mapf/seeds.py`: `derive_seed`
- `experiments/run_compare.py`, `experiments/crosscheck.py`
- `tests/`: corridor swap, 2x2 grid, dead end, agent already on its goal
- `data/maps`, `data/scens`: benchmark files

## Conventions

- Coordinates are `(row, col)`. `.scen` files store `(x, y)`; the loader converts.
- A solution is `list[Config]`, `solution[0]` being the starts. `solve()`
  returns the configurations even when unsolved; success is decided by
  `metrics.is_success`.
- Seeds: `mapf.seeds.derive_seed` (zlib.crc32 on a string). Never `hash()`.
- Run the validity check on every returned solution, ours and pypibt's.
- Compare cost only on instances that both solvers solved.
- Runtime is comparable only between Python implementations (HCA* and EECBS
  are C++).
- Every function docstring says which line or step of Algorithm 1 it
  corresponds to.
- Dependencies: Python 3.10+, numpy only (pytest for tests).
- Report framing: our variants are simplified re-implementations compared in
  one framework, not new algorithms. Cite the originals.

## Benchmarks

Later runs use empty-8-8, random-32-32-20, warehouse-20-40-10-2-2, den520d,
ost003d and Paris_1_256 from the MAPF benchmark site. Only the first two are
in `data/` so far, each with scenario `random-1`.

## Commands

- `git submodule update --init` (once after cloning)
- `pytest` (stub tests show as xfailed until implemented)
- `python experiments/crosscheck.py -m <map> -i <scen> -N <agents> -s <seed>`
- `python experiments/run_compare.py --list`
