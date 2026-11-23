# Extra evaluation (optional)

Additions beyond the core evaluation in `experiments/run_compare.py`. Nothing in
`src/mapf` or the core script depends on this folder. Every run reuses the
core `solve_spec` / `row_from_output`, so validity, success and the core
metrics are computed exactly as in the main comparison. Outputs go to their own
CSVs (`results/extras.csv`, `results/sweep.csv`).

| File | What it adds | Source |
|---|---|---|
| `fetch_movingai.py` | Downloads maps and all 25 `random` + 25 `even` scenario files per map into `data/` | MovingAI benchmarks |
| `common.py` | Specs for random **and** even scenarios; individual success rate; MAPF Tracker loader | |
| `run_extras.py` | Paired comparison with extra columns: scenario type, individual success rate, tracker best-known cost and lower bound, `SOC / best known`, `SOC / tracker LB` | MAPF Tracker |
| `agent_sweep.py` | Standard protocol: add agents until the solver fails; max agents solved per scenario and a success-rate-vs-agents curve | mapf.info / MovingAI |

## Data

```bash
python experiments/extras/fetch_movingai.py          # maps + scenarios (about 13 MB)
```

Tracker baselines live in `data/tracker/<map>-<type>-<id>.csv`, one file per
scenario, from the tracker's "Bulk export benchmarks" (results only, without
solutions). Columns: `map_name, scen_type, type_id, agents, lower_cost,
solution_cost`. Currently exported: `empty-8-8` and `random-32-32-20`, all 50
scenarios each. For another map, export its "Results (.csv)" the same way and
unzip the CSVs into `data/tracker/`.

Checked: `type_id` is the MovingAI file number, and the tracker's cost is the
sum over agents of the final arrival time, the same as
`mapf.metrics.sum_of_costs` (`tests/test_extras.py`). `run_extras.py` warns if
any solved run ever costs less than the tracker's lower bound.

## Running

```bash
python experiments/extras/run_extras.py --maps empty-8-8 random-32-32-20 \
    --types random even --scens 1 2 3 4 5 --agents 10 30 100

python experiments/extras/agent_sweep.py --maps random-32-32-20 maze-32-32-4 \
    --types random --scens 1 2 3 4 5 --start 10 --step 10
```

`agent_sweep.py --step 1` is the protocol as written (one agent at a time).
PIBT's success is not monotone in the number of agents, so `--patience k`
lets the sweep continue past k consecutive failures; the default 0 stops at
the first failure.

## Reporting rules

- Tracker numbers are **costs only**. Its runtimes come from other (mostly C++)
  solvers on other machines; never compare runtimes with it.
- The tracker does not verify lower bounds (Shen et al. 2023). Where an instance
  is *closed* (lower bound = best cost), `SOC / best known` is the exact
  suboptimality; elsewhere it is relative to the best known solution.
- Cost ratios use only runs every compared solver solved; individual success
  rate is averaged over all runs, solved or not.

## References

- R. Stern et al., "Multi-Agent Pathfinding: Definitions, Variants, and
  Benchmarks", SoCS 2019. Maps and scenarios: <https://movingai.com/benchmarks/mapf/index.html>
- B. Shen, Z. Chen, M. A. Cheema, D. Harabor, P. J. Stuckey, "Tracking Progress
  in Multi-Agent Path Finding", arXiv 2305.08446. <https://tracker.pathfinding.ai>
- Benchmark protocol (add agents until failure): <https://mapf.info/index.php/Main/Benchmarks>
