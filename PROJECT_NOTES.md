# CS279 project notes: PIBT with improvements (Darshan and Suyash)

## Dates
- Proposal submitted: Oct 24, 2026.
- Project report due: **Nov 23, 2026**. Updates to the report allowed until **Dec 7, 2026**.

## Professor's comment on the proposal (verbatim)
> The project proposal looks good and is interesting. PIBT is currently widely used because it achieves good solution quality with a small runtime. As a result, researchers have developed several variants of PIBT. You might want to check them out so that you do not inadvertently reinvent previous ideas.

Action from this comment: check the published PIBT variants (table below), cite them, and state in the report how each of our versions relates to them.

## Decision
- Re-implement PIBT ourselves in Python from Algorithm 1 of the paper (arXiv 1901.11282v5).
- Cross-check against the MIT-licensed Python version `github.com/Kei18/pypibt` (cite it; keep its copyright notice if any code is reused).
- Define "Base PIBT" as the paper's version: unique fractional tie-breakers for priority, tie-break by distance, then cells without agents, then random. Also report a pure-random-ties variant as a second reference.
- Compare runtime only among our own Python variants (HCA* and EECBS are C++).

## Published variants to check (preliminary: read from abstracts or summaries, not full papers)
| Our idea | Related published work | Overlap |
|---|---|---|
| Smarter tie-breaking | "Lightweight and Effective Preference Construction in PIBT", arXiv 2505.12623 (hindrance, regret) | Direct. Rules that avoid blocking neighbours repeat "hindrance". The paper's default tie-break already prefers empty cells, then random. |
| Multi-step lookahead | winPIBT, arXiv 1905.10149 (windowed PIBT, window of one step is plain PIBT); EPIBT, arXiv 2511.09193 (multi-action operations); Multi-Dependency PIBT, arXiv 2603.23405 | Direct. Windowed multi-step PIBT exists since 2019. |
| Congestion guidance | "Enhancing Lifelong MAPF by Using Artificial Potential Fields", arXiv 2505.22753 (repulsion fields from predicted paths); lifelong MAPF challenges, arXiv 2404.16162 | Partial. |
| Also exists | "Improvement of PIBT-based Solution Method for Lifelong MAPD Problems to Extend Applicable Graphs" (SCITEPRESS 2025, not read); PIBT used inside LaCAM | Not central to one-shot. |

How to frame it in the report: our versions are simplified re-implementations compared in one framework, not new algorithms. Say so explicitly and cite the originals.

## Facts to keep straight
- The paper says reachability (agents each reach their goal at some time) is guaranteed on graphs where every adjacent pair lies on a simple cycle. It does not guarantee all agents on goals at once (one-shot success).
- Per-step cost: O(|A| * (Delta log Delta + log|A|)) with precomputed BFS distance tables.
- pypibt differences from the paper: pure random tie-break, initial priorities seeded by start-to-goal distance.
- pypibt timing on 32x32 map (my run): about 2, 4, 6 ms per step for 100, 200, 400 agents.

## Work split (two people)
Agree the interface together first (about an hour): `pibt.py` exposes `step(...)` with two hook points, `order_candidates(agent, candidates, state)` for tie-breaking/guidance and `plan_step(state)` for lookahead. Both people code against it.

| Owner | Tasks |
|---|---|
| Person A | Core PIBT (Algorithm 1), .map/.scen loader, BFS distance tables, validator (vertex, swap, illegal move), metrics (success, SOC ratio, makespan ratio, runtime/step, backtracking depth, goal displacements), paired-seed runner, pypibt cross-check, tie-breaking variants |
| Person B | Related-work table (read winPIBT, hindrance/regret, APF in full), baselines (HCA*; check pibt2's solver list for others), multi-step lookahead, congestion guidance (stretch goal) |
| Both | Pair on the core for its first working version; each writes the report section for the area they own; review each other's code and numbers |

## Timeline
- Nov 23 (due): minimal honest report: working validated Base PIBT, cross-check vs pypibt, first results on empty-8-8 and random-32-32-20, related-work paragraph, plan for the rest.
- Nov 24-30: improvements and baselines, one map family at a time.
- Dec 1-6: full benchmark runs, plots, write-up. Dec 7: final update.

## Disclosure
Check the course policy on AI assistance and third-party code. Report numbers must come from our own implementation. Cite pypibt and pibt2 as references.
