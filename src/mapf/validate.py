"""Check that a solution is a legal MAPF solution.

Run on every solution any solver returns, ours and pypibt's, before its
costs are used. Written independently of pypibt's own checker so that the
cross-check does not rely on the code it is checking. It reads grid.free
directly rather than mapf.grid.is_free/neighbours, so it does not depend on
the solver's own graph functions either.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mapf.grid import Config, Coord, Grid, Solution


@dataclass
class ValidationResult:
    """Outcome of a check. errors is empty exactly when ok is True.

    Not part of Algorithm 1.
    """

    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def merge(self, other: ValidationResult) -> None:
        for message in other.errors:
            self.add(message)


def _same_config(a: Config, b: Config) -> bool:
    """Compare two configurations cell by cell, accepting lists or tuples for cells."""
    return len(a) == len(b) and all(tuple(u) == tuple(v) for u, v in zip(a, b))


def _inside_and_free(grid: Grid, cell: Coord) -> bool:
    r, c = cell
    return 0 <= r < grid.height and 0 <= c < grid.width and bool(grid.free[r, c])


def check_shape(solution: Solution, num_agents: int) -> ValidationResult:
    """Every configuration lists exactly num_agents cells, and there is at least one.

    Algorithm 1: output format (paths pi_1..pi_n of equal length).
    """
    result = ValidationResult()
    if len(solution) == 0:
        result.add("solution has no configurations")
        return result
    for t, config in enumerate(solution):
        if len(config) != num_agents:
            result.add(f"t={t}: {len(config)} agents listed, expected {num_agents}")
    return result


def check_starts(solution: Solution, starts: Config) -> ValidationResult:
    """solution[0] equals the start configuration.

    Algorithm 1 Line 1.
    """
    result = ValidationResult()
    if len(solution) == 0:
        result.add("solution has no configurations, so no start configuration")
    elif not _same_config(solution[0], starts):
        wrong = [i for i, (u, s) in enumerate(zip(solution[0], starts)) if tuple(u) != tuple(s)]
        result.add(f"t=0 is not the start configuration (agents {wrong[:10]})")
    return result


def check_goals(solution: Solution, goals: Config) -> ValidationResult:
    """The last configuration equals the goal configuration.

    Algorithm 1: termination condition for one-shot MAPF (section 4.4.1).
    An unsolved run fails this check and no other.
    """
    result = ValidationResult()
    if len(solution) == 0:
        result.add("solution has no configurations, so no final configuration")
    elif not _same_config(solution[-1], goals):
        off = [i for i, (u, g) in enumerate(zip(solution[-1], goals)) if tuple(u) != tuple(g)]
        result.add(f"t={len(solution) - 1}: {len(off)} agents not on their goal (agents {off[:10]})")
    return result


def check_moves(grid: Grid, solution: Solution) -> ValidationResult:
    """Every cell is free, and each agent stays or moves to a 4-neighbour each step.

    Algorithm 1 Line 9: the next cell must come from Neigh(pi_i[t]) or be pi_i[t].
    """
    result = ValidationResult()
    for t, config in enumerate(solution):
        for i, cell in enumerate(config):
            if not _inside_and_free(grid, tuple(cell)):
                result.add(f"t={t}: agent {i} at {tuple(cell)}, which is outside the grid or an obstacle")
    for t in range(len(solution) - 1):
        for i, (u, v) in enumerate(zip(solution[t], solution[t + 1])):
            if abs(u[0] - v[0]) + abs(u[1] - v[1]) > 1:
                result.add(f"t={t}->{t + 1}: agent {i} jumps from {tuple(u)} to {tuple(v)}")
    return result


def check_vertex_conflicts(solution: Solution) -> ValidationResult:
    """No two agents share a cell at the same timestep.

    Algorithm 1 Line 12 is what prevents this.
    """
    result = ValidationResult()
    for t, config in enumerate(solution):
        seen: dict[Coord, int] = {}
        for i, cell in enumerate(config):
            cell = tuple(cell)
            if cell in seen:
                result.add(f"t={t}: agents {seen[cell]} and {i} both at {cell}")
            else:
                seen[cell] = i
    return result


def check_swap_conflicts(solution: Solution) -> ValidationResult:
    """No two agents exchange cells between t and t+1.

    Algorithm 1 Line 13 is what prevents this.
    """
    result = ValidationResult()
    for t in range(len(solution) - 1):
        now, nxt = solution[t], solution[t + 1]
        at_now = {tuple(cell): i for i, cell in enumerate(now)}
        for i, (u, v) in enumerate(zip(now, nxt)):
            u, v = tuple(u), tuple(v)
            if u == v:
                continue
            j = at_now.get(v)
            if j is not None and j > i and tuple(nxt[j]) == u:  # j > i: report each pair once
                result.add(f"t={t}->{t + 1}: agents {i} and {j} swap {u} <-> {v}")
    return result


def validate_solution(
    grid: Grid, starts: Config, goals: Config, solution: Solution, require_goals: bool = True
) -> ValidationResult:
    """Run all checks and merge their errors.

    Algorithm 1: checks the output as a whole. With require_goals=False the
    goal check is skipped, which is how an unsolved (timed-out) run is still
    checked for illegal moves and conflicts.
    """
    result = check_shape(solution, len(starts))
    if not result.ok:
        return result  # the other checks assume one cell per agent per timestep
    result.merge(check_starts(solution, starts))
    if require_goals:
        result.merge(check_goals(solution, goals))
    result.merge(check_moves(grid, solution))
    result.merge(check_vertex_conflicts(solution))
    result.merge(check_swap_conflicts(solution))
    return result
