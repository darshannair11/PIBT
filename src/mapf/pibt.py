from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from mapf.dist import DistTable
from mapf.grid import Config, Coord, Grid, Solution, neighbours

TIE_PAPER = "paper"
TIE_RANDOM = "random"
TIE_BREAK_RULES = (TIE_PAPER, TIE_RANDOM)


@dataclass
class StepState:
    timestep: int
    grid: Grid
    dist: DistTable
    goals: Config
    priorities: list[float]
    current: Config
    nxt: list[Coord | None]
    occupied_now: dict[Coord, int]
    occupied_nxt: dict[Coord, int]
    rng: np.random.Generator


@dataclass
class StepStats:
    runtime_s: float = 0.0
    pibt_calls: int = 0
    depth_sum: int = 0
    max_depth: int = 0


@dataclass
class PIBT:
    grid: Grid
    starts: Config
    goals: Config
    seed: int = 0
    tie_break: str = TIE_PAPER
    dist: DistTable | None = None
    stats: list[StepStats] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.tie_break not in TIE_BREAK_RULES:
            raise ValueError(f"tie_break must be one of {TIE_BREAK_RULES}, got {self.tie_break!r}")
        if len(self.starts) != len(self.goals):
            raise ValueError("starts and goals must have the same length")
        self.rng = np.random.default_rng(self.seed)

    def reset(self) -> None:
        # Algorithm 1, Lines 1-2
        if self.dist is None:
            self.dist = DistTable(self.grid, self.goals)
        self.stats.clear()
        self.current = list(self.starts)
        self.epsilons = self.init_priorities()
        self.priorities = list(self.epsilons)
        self.timestep = 0

    def init_priorities(self) -> list[float]:
        # Algorithm 1, Line 2
        priority_order = self.rng.random(len(self.starts))
        priority_list = [float(p) for p in priority_order]
        return priority_list

    def update_priorities(self, state: StepState) -> None:
        # Algorithm 1, Line 3
        for i, (position, goal) in enumerate(zip(state.current, state.goals)):
            if position == goal:
                state.priorities[i] = self.epsilons[i]
            else:
                state.priorities[i] += 1

    def order_candidates(
        self, agent: int, candidates: list[Coord], state: StepState
    ) -> list[Coord]:
        # Algorithm 1, Line 10 and Appendix B
        def sort_key(cell: Coord) -> tuple[int, bool, float]:
            dist = state.dist.get(agent, cell)
            has_agent = cell in state.occupied_now
            random_value = state.rng.random()
            if self.tie_break == TIE_PAPER:
                return (dist, has_agent, random_value)
            elif self.tie_break == TIE_RANDOM:
                return (dist, random_value)

        return sorted(candidates, key=sort_key)

    def plan_step(self, state: StepState) -> Config:
        # Algorithm 1, Lines 4-7
        agents = sorted(range(len(state.current)), key=lambda i: state.priorities[i], reverse=True)
        for agent in agents:
            if state.nxt[agent] is None:
                self._pibt(agent, None, state)
        return list(state.nxt)

    def _pibt(self, agent: int, caller: int | None, state: StepState, depth: int = 1) -> bool:
        # Algorithm 1, Lines 8-22
        step_stats = self.stats[-1]
        step_stats.pibt_calls += 1
        step_stats.depth_sum += depth
        step_stats.max_depth = max(step_stats.max_depth, depth)

        position = state.current[agent]
        candidates = neighbours(state.grid, position) + [position]
        candidates = self.order_candidates(agent, candidates, state)

        for cell in candidates:
            if cell in state.occupied_nxt:
                continue
            if caller is not None and state.current[caller] == cell:
                continue

            state.nxt[agent] = cell
            state.occupied_nxt[cell] = agent

            other = state.occupied_now.get(cell)
            if other is not None and state.nxt[other] is None:
                if not self._pibt(other, agent, state, depth + 1):
                    continue
            return True

        state.nxt[agent] = position
        state.occupied_nxt[position] = agent
        return False

    def step(self) -> Config:
        # Algorithm 1, Lines 3-7
        started = time.perf_counter()
        state = StepState(
            timestep=self.timestep,
            grid=self.grid,
            dist=self.dist,
            goals=self.goals,
            priorities=self.priorities,
            current=self.current,
            nxt=[None] * len(self.current),
            occupied_now={cell: agent for agent, cell in enumerate(self.current)},
            occupied_nxt={},
            rng=self.rng,
        )
        self.stats.append(StepStats())
        self.update_priorities(state)
        self.current = self.plan_step(state)
        self.timestep += 1
        self.stats[-1].runtime_s = time.perf_counter() - started
        return self.current

    def solve(self, max_timestep: int = 1000) -> Solution:
        self.reset()
        goals = list(self.goals)
        solution = [list(self.current)]
        while self.current != goals and len(solution) <= max_timestep:
            solution.append(list(self.step()))
        return solution
