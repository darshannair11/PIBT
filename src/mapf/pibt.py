"""Our PIBT, written from Algorithm 1 of arXiv 1901.11282v5.

Algorithm 1, for reference (line numbers as printed in the paper):

    Setup
     1  pi_i[0] <- s_i for every agent
     2  p_i <- epsilon_i, with epsilon_i in [0, 1) and all distinct
    For each timestep t
     3  p_i <- epsilon_i if pi_i[t] = g_i, else p_i + 1      (update priorities)
     4  sort agents in decreasing order of p_i
     5  for each agent a_i
     6      if pi_i[t+1] is undecided: PIBT(a_i, none)
     7  end for
    Procedure PIBT(a_i, a_j)
     8  (procedure header; a_j is the agent a_i inherits priority from, or none)
     9  C <- Neigh(pi_i[t]) plus pi_i[t] itself
    10  sort C by increasing dist(u, g_i); tie-break: presence of agents
    11  for v in C
    12      if some agent already has pi_k[t+1] = v: continue   (vertex conflict)
    13      if a_j is not none and pi_j[t] = v: continue        (swap conflict)
    14      pi_i[t+1] <- v                                      (reserve)
    15      if an undecided agent a_k is at v now
    16          if PIBT(a_k, a_i) is invalid: continue          (replan)
    17      end if
    18      return valid
    19  end for
    20  pi_i[t+1] <- pi_i[t]                                    (stuck: stay)
    21  return invalid
    22  end procedure

Appendix B gives the full sort key behind Line 10: (1) distance to goal,
(2) cells with no agent first, (3) a random value.

The two hook points agreed in PROJECT_NOTES.md are order_candidates (Line 10)
and plan_step (Lines 4-7). Variants subclass PIBT and override one of them.

Nothing in this file may be copied from third_party/pypibt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mapf.dist import DistTable
from mapf.grid import Config, Coord, Grid, Solution

# Tie-break rules for Line 10.
TIE_PAPER = "paper"  # distance, then cells with no agent, then random (Base PIBT)
TIE_RANDOM = "random"  # distance, then random (second reference; what pypibt does)
TIE_BREAK_RULES = (TIE_PAPER, TIE_RANDOM)


@dataclass
class StepState:
    """Everything one timestep of Algorithm 1 reads and writes.

    This is what the two hooks receive. It corresponds to the variables of
    Lines 3-22 at one fixed t.
    """

    timestep: int
    grid: Grid
    dist: DistTable
    goals: Config
    priorities: list[float]  # p_i after Line 3
    current: Config  # pi_i[t]
    nxt: list[Coord | None]  # pi_i[t+1]; None means undecided (Lines 6, 14, 20)
    occupied_now: dict[Coord, int]  # cell -> agent at t (Line 15)
    occupied_nxt: dict[Coord, int]  # cell -> agent that reserved it (Line 12)
    rng: np.random.Generator  # random part of the Line 10 tie-break


@dataclass
class StepStats:
    """Counters for one timestep, read by mapf.metrics.

    Not part of Algorithm 1. They measure the recursion of Lines 8-22.
    """

    runtime_s: float = 0.0
    pibt_calls: int = 0  # how many times the procedure at Line 8 ran
    depth_sum: int = 0  # sum over calls of the recursion depth (top-level call = 1)
    max_depth: int = 0


@dataclass
class PIBT:
    """One-shot PIBT solver for a single instance.

    Usage (what the tests and experiments rely on):

        solver = PIBT(grid, starts, goals, seed=derive_seed(...))
        solution = solver.solve(max_timestep=1000)

    solve() returns every configuration it produced, including the start, even
    when the time limit is reached. Whether the instance was solved is decided
    by mapf.metrics.is_success, not by solve().
    """

    grid: Grid
    starts: Config
    goals: Config
    seed: int = 0
    tie_break: str = TIE_PAPER
    dist: DistTable | None = None  # built in reset() when not supplied
    stats: list[StepStats] = field(default_factory=list)  # one entry per step()

    def __post_init__(self) -> None:
        """Check arguments. Not a line of Algorithm 1."""
        if self.tie_break not in TIE_BREAK_RULES:
            raise ValueError(f"tie_break must be one of {TIE_BREAK_RULES}, got {self.tie_break!r}")
        if len(self.starts) != len(self.goals):
            raise ValueError("starts and goals must have the same length")
        self.rng = np.random.default_rng(self.seed)

    # -- setup ---------------------------------------------------------------

    def reset(self) -> None:
        """Put every agent on its start and set the initial priorities.

        Algorithm 1 Lines 1-2. Also builds the distance tables if none were
        passed in, and clears self.stats.
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    def init_priorities(self) -> list[float]:
        """Return epsilon_i for every agent: distinct values in [0, 1).

        Algorithm 1 Line 2. Base PIBT only needs them distinct. (pypibt uses
        dist(start, goal) / grid size instead, which is the PIBT+ idea of
        Algorithm 2 Line 2; keep that as an option only if we report it.)
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    # -- one timestep --------------------------------------------------------

    def update_priorities(self, state: StepState) -> None:
        """Reset p_i to epsilon_i for agents on their goal, add 1 for the rest.

        Algorithm 1 Line 3.
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    def order_candidates(self, agent: int, candidates: list[Coord], state: StepState) -> list[Coord]:
        """HOOK 1. Return candidates in the order agent should try them.

        Algorithm 1 Line 10. The base version sorts by dist(u, g_agent) and
        breaks ties according to self.tie_break:
            "paper":  cells with no agent first, then random (Appendix B rules 1-3)
            "random": random only (Appendix B rules 1 and 3)
        Tie-breaking and congestion-guidance variants override this method.
        It must return a permutation of candidates and must not filter them:
        the conflict checks belong to Lines 12-13.
        """
        # TODO(Person A)
        raise NotImplementedError

    def plan_step(self, state: StepState) -> Config:
        """HOOK 2. Decide pi_i[t+1] for every agent and return it as a Config.

        Algorithm 1 Lines 4-7: visit agents in decreasing priority and call
        the procedure for each one that is still undecided. The lookahead
        variant overrides this method.
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    def _pibt(self, agent: int, caller: int | None, state: StepState, depth: int = 1) -> bool:
        """The recursive procedure PIBT(a_i, a_j). Returns True for "valid".

        Algorithm 1 Lines 8-22, with agent = a_i and caller = a_j:
            Line 9   candidates = neighbours of the current cell, plus the cell
            Line 10  self.order_candidates(...)
            Line 12  skip cells reserved in state.occupied_nxt
            Line 13  skip the caller's current cell
            Line 14  reserve the cell
            Line 15  is an undecided agent standing there?
            Line 16  recurse with (that agent, agent); on False try the next cell
            Line 18  return True
            Lines 20-21  no cell worked: stay and return False
        depth is not in the paper; it feeds StepStats.
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    def step(self) -> Config:
        """Advance one timestep and return the new configuration.

        Algorithm 1 Lines 3-7 for one t: build the StepState, call
        update_priorities, call plan_step, commit the result, and append one
        StepStats (with the measured runtime) to self.stats.
        """
        # TODO(Person A, paired)
        raise NotImplementedError

    # -- whole run -----------------------------------------------------------

    def solve(self, max_timestep: int = 1000) -> Solution:
        """Run from the starts until every agent is on its goal or the limit is hit.

        Algorithm 1 Lines 1-2 once (reset), then Lines 3-7 repeatedly (step).
        Termination follows section 4.4.1: stop at the goal configuration, or
        give up at max_timestep. Returns all configurations, start included,
        so an unsolved run has exactly max_timestep + 1 of them. If the starts
        already are the goals, return [starts] without taking a step (pypibt
        takes one step first, so its makespan is 1 there).
        """
        # TODO(Person A, paired)
        raise NotImplementedError
