from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, replace

import numpy as np

from mapf.dist import DistTable
from mapf.grid import Config, Coord, Grid, Solution, neighbours

TIE_PAPER = "paper"
TIE_RANDOM = "random"
TIE_BREAK_RULES = (TIE_PAPER, TIE_RANDOM)

CHOICE_WEIGHTS = {
    "distance": 20.0,
    "hindrance": 3.0,
    "parked_agent": 2.65,
    "moving_agent": 0.28,
    "blocked_neighbours": 0.06,
}
MAX_HOLD = 4


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
    hindrance: bool = False
    weighted_choice: bool = False
    swap_on_failed_push: bool = False
    protect_parked: float = 0.0
    goal_lookahead: int = 0
    choice_weights: dict = field(default_factory=lambda: dict(CHOICE_WEIGHTS))

    def __post_init__(self) -> None:
        if self.tie_break not in TIE_BREAK_RULES:
            raise ValueError(f"tie_break must be one of {TIE_BREAK_RULES}, got {self.tie_break!r}")
        if len(self.starts) != len(self.goals):
            raise ValueError("starts and goals must have the same length")
        if not 0.0 <= self.protect_parked <= 1.0:
            raise ValueError("protect_parked must be between 0 and 1")
        if self.goal_lookahead < 0:
            raise ValueError("goal_lookahead must be 0 or more")
        self.rng = np.random.default_rng(self.seed)
        self.holding = set()
        self.hold_counts = [0] * len(self.starts)

    def reset(self) -> None:
        # Algorithm 1, Lines 1-2
        if self.dist is None:
            self.dist = DistTable(self.grid, self.goals)
        self.stats.clear()
        self.current = list(self.starts)
        self.epsilons = self.init_priorities()
        self.priorities = list(self.epsilons)
        self.timestep = 0
        self.holding = set()
        self.hold_counts = [0] * len(self.starts)

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
        for i in self.holding:
            state.priorities[i] = self.epsilons[i]

    def order_candidates(
        self, agent: int, candidates: list[Coord], state: StepState
    ) -> list[Coord]:
        # Algorithm 1, Line 10 and Appendix B
        if self.weighted_choice:
            order = self.weighted_order(agent, candidates, state)
        else:
            order = self.ranked_order(agent, candidates, state)
        if agent in self.holding:
            order = self.hold_back(agent, order, state)
        return order

    def ranked_order(self, agent: int, candidates: list[Coord], state: StepState) -> list[Coord]:
        position = state.current[agent]
        prefer_empty = self.tie_break == TIE_PAPER
        avoid_parked = self.protect_parked > 0
        if avoid_parked and self.protect_parked < 1:
            avoid_parked = state.rng.random() < self.protect_parked
        adjacent_agents = []
        if self.hindrance:
            adjacent_cells = neighbours(state.grid, position)
            adjacent_agents = [
                state.occupied_now[c] for c in adjacent_cells if c in state.occupied_now
            ]

        def sort_key(cell: Coord) -> tuple:
            key = [state.dist.get(agent, cell)]
            if avoid_parked:
                key.append(self.is_parked(cell, agent, state))
            if self.hindrance:
                key.append(self.hindrance_of(cell, position, adjacent_agents, state))
            if prefer_empty:
                key.append(cell in state.occupied_now)
            key.append(state.rng.random())
            return tuple(key)

        return sorted(candidates, key=sort_key)

    def weighted_order(self, agent: int, candidates: list[Coord], state: StepState) -> list[Coord]:
        position = state.current[agent]
        weights = self.choice_weights
        adjacent_cells = neighbours(state.grid, position)
        adjacent_agents = [state.occupied_now[c] for c in adjacent_cells if c in state.occupied_now]
        scored = []
        for cell in candidates:
            occupant = state.occupied_now.get(cell)
            parked = self.is_parked(cell, agent, state)
            moving = occupant is not None and occupant != agent and not parked
            around = neighbours(state.grid, cell)
            blocked = 4 - sum(1 for c in around if c not in state.occupied_now or c == position)
            score = weights["distance"] * state.dist.get(agent, cell)
            score += weights["hindrance"] * self.hindrance_of(
                cell, position, adjacent_agents, state
            )
            score += weights["parked_agent"] * parked
            score += weights["moving_agent"] * moving
            score += weights["blocked_neighbours"] * blocked
            noise = -math.log(-math.log(state.rng.random() or 1e-12))
            scored.append((score - noise, cell))
        scored.sort()
        return [cell for _, cell in scored]

    def hold_back(self, agent: int, order: list[Coord], state: StepState) -> list[Coord]:
        position, goal = state.current[agent], state.goals[agent]
        others = [c for c in order if c != position and c != goal]
        return [position] + others + [goal]

    def agents_to_hold(self) -> set[int]:
        agents = range(len(self.current))
        arriving = [i for i in agents if self.dist.get(i, self.current[i]) == 1]
        if not arriving:
            return set()
        future = self.projected_future()
        holding = set()
        for i in arriving:
            reached = False
            pushed_off = False
            for config in future:
                if config[i] == self.goals[i]:
                    reached = True
                elif reached:
                    pushed_off = True
                    break
            if pushed_off and self.hold_counts[i] < MAX_HOLD:
                holding.add(i)
                self.hold_counts[i] += 1
            else:
                self.hold_counts[i] = 0
        return holding

    def projected_future(self) -> list[Config]:
        trial = replace(self, goal_lookahead=0, stats=[])
        trial.current = list(self.current)
        trial.priorities = list(self.priorities)
        trial.epsilons = self.epsilons
        trial.timestep = self.timestep
        trial.rng = np.random.default_rng(int(self.rng.integers(2**31)))
        return [list(trial.step()) for _ in range(self.goal_lookahead)]

    def is_parked(self, cell: Coord, agent: int, state: StepState) -> bool:
        occupant = state.occupied_now.get(cell)
        if occupant is None or occupant == agent:
            return False
        return state.current[occupant] == state.goals[occupant]

    def hindrance_of(
        self, cell: Coord, position: Coord, adjacent_agents: list[int], state: StepState
    ) -> int:
        # Okumura and Nagai 2025 (arXiv 2505.12623), Algorithm 2
        hindrance = 0
        for other in adjacent_agents:
            if cell == state.current[other]:
                continue
            if state.dist.get(other, cell) < state.dist.get(other, position):
                hindrance += 1
        return hindrance

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
                    if self.swap_on_failed_push:
                        self.swap_priorities(agent, other, state)
                    continue
            return True

        state.nxt[agent] = position
        state.occupied_nxt[position] = agent
        return False

    def swap_priorities(self, pusher: int, blocked: int, state: StepState) -> None:
        # priority exchange on a failed push, after Matsui 2025 (ICAART)
        priorities = state.priorities
        if priorities[pusher] > priorities[blocked]:
            priorities[pusher], priorities[blocked] = priorities[blocked], priorities[pusher]

    def step(self) -> Config:
        # Algorithm 1, Lines 3-7
        started = time.perf_counter()
        self.holding = self.agents_to_hold() if self.goal_lookahead > 0 else set()
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
