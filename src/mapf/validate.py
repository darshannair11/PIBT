"""Check that a solution is a legal MAPF solution.

Run on every solution any solver returns, ours and pypibt's, before its
costs are used. Written independently of pypibt's own checker so that the
cross-check does not rely on the code it is checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mapf.grid import Config, Grid, Solution


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


def check_shape(solution: Solution, num_agents: int) -> ValidationResult:
    """Every configuration lists exactly num_agents cells, and there is at least one.

    Algorithm 1: output format (paths pi_1..pi_n of equal length).
    """
    # TODO(Suyash)
    raise NotImplementedError


def check_starts(solution: Solution, starts: Config) -> ValidationResult:
    """solution[0] equals the start configuration.

    Algorithm 1 Line 1.
    """
    # TODO(Suyash)
    raise NotImplementedError


def check_goals(solution: Solution, goals: Config) -> ValidationResult:
    """The last configuration equals the goal configuration.

    Algorithm 1: termination condition for one-shot MAPF (section 4.4.1).
    An unsolved run fails this check and no other.
    """
    # TODO(Suyash)
    raise NotImplementedError


def check_moves(grid: Grid, solution: Solution) -> ValidationResult:
    """Every cell is free, and each agent stays or moves to a 4-neighbour each step.

    Algorithm 1 Line 9: the next cell must come from Neigh(pi_i[t]) or be pi_i[t].
    """
    # TODO(Suyash)
    raise NotImplementedError


def check_vertex_conflicts(solution: Solution) -> ValidationResult:
    """No two agents share a cell at the same timestep.

    Algorithm 1 Line 12 is what prevents this.
    """
    # TODO(Suyash)
    raise NotImplementedError


def check_swap_conflicts(solution: Solution) -> ValidationResult:
    """No two agents exchange cells between t and t+1.

    Algorithm 1 Line 13 is what prevents this.
    """
    # TODO(Suyash)
    raise NotImplementedError


def validate_solution(
    grid: Grid, starts: Config, goals: Config, solution: Solution, require_goals: bool = True
) -> ValidationResult:
    """Run all checks and merge their errors.

    Algorithm 1: checks the output as a whole. With require_goals=False the
    goal check is skipped, which is how an unsolved (timed-out) run is still
    checked for illegal moves and conflicts.
    """
    # TODO(Suyash)
    raise NotImplementedError
