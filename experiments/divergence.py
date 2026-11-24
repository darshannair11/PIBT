import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mapf.dist import DistTable  # noqa: E402
from mapf.grid import load_map, load_scen, neighbours  # noqa: E402
from mapf.metrics import sum_of_costs  # noqa: E402
from mapf.pibt import PIBT  # noqa: E402
from mapf.seeds import derive_seed  # noqa: E402
from mapf.validate import validate_solution  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
PLAN_DIR = DATA_DIR / "tracker_plans"
MOVES = {"u": (1, 0), "d": (-1, 0), "l": (0, -1), "r": (0, 1), "w": (0, 0)}

VARIANTS = {
    "paper": {"tie_break": "paper"},
    "random": {"tie_break": "random"},
    "hindrance": {"tie_break": "random", "hindrance": True},
    "hindrance+swap": {"tie_break": "random", "hindrance": True, "swap_on_failed_push": True},
}
BASE = "paper"

CLOSER = "steps closer"
WAIT = "waits off its goal"
AWAY = "steps away from its goal"
STAY = "stays on its goal"
LEAVE = "leaves its goal"


class PrefixDist:
    def __init__(self, full: DistTable, count: int) -> None:
        self.tables = full.tables[:count]

    def get(self, agent, cell):
        return int(self.tables[agent][cell])


def decode_plan(plan: str, starts, goals):
    lines = plan.split("\n")
    idle = [i for i, (start, goal) in enumerate(zip(starts, goals)) if start == goal]
    if len(lines) + len(idle) == len(starts):
        for i in idle:
            lines.insert(i, "")
    lines += [""] * (len(starts) - len(lines))
    paths = []
    for line, start in zip(lines, starts):
        cell = start
        path = [cell]
        for count, move in re.findall(r"(\d*)([udlrw])", line):
            step = MOVES[move]
            for _ in range(int(count or 1)):
                cell = (cell[0] + step[0], cell[1] + step[1])
                path.append(cell)
        paths.append(path)
    length = max(len(p) for p in paths)
    return [[p[min(t, len(p) - 1)] for p in paths] for t in range(length)]


def move_type(dist, agent, cell, nxt):
    before = dist.get(agent, cell)
    if nxt == cell:
        return STAY if before == 0 else WAIT
    if before == 0:
        return LEAVE
    return CLOSER if dist.get(agent, nxt) < before else AWAY


def free_closer_cells(grid, dist, agent, config, nxt_config, position_now):
    cell = config[agent]
    here = dist.get(agent, cell)
    taken_next = {c for other, c in enumerate(nxt_config) if other != agent}
    result = []
    for option in neighbours(grid, cell):
        if dist.get(agent, option) >= here or option in taken_next:
            continue
        occupant = position_now.get(option)
        if occupant is not None and nxt_config[occupant] == cell:
            continue
        result.append(option)
    return result


def why_not_greedy(
    agent, wanted, t, config, nxt_config, later, position_now, goals, dist, goal_busy_until
):
    cell = config[agent]
    reasons = []
    if any(other != agent and nxt == cell for other, nxt in enumerate(nxt_config)):
        reasons.append("another agent moves into the cell it is standing on")
    if any(other != agent and nxt == wanted for other, nxt in enumerate(nxt_config)):
        occupant = position_now.get(wanted)
        if occupant is None or nxt_config[occupant] != wanted:
            reasons.append("another agent moves into the cell PIBT would take")
    occupant = position_now.get(wanted)
    if occupant is not None and nxt_config[occupant] == wanted:
        if wanted == goals[occupant]:
            reasons.append("PIBT would push an agent that is resting on its goal")
        else:
            reasons.append("PIBT would push an agent that is waiting there")
    if t + dist.get(agent, cell) <= goal_busy_until[agent]:
        reasons.append("its goal is still needed by another agent, so arriving early gains nothing")
    if not reasons and any(other != agent and nxt == wanted for other, nxt in enumerate(later)):
        reasons.append("another agent uses the cell PIBT would take one step later")
    return reasons or ["none of the above"]


class Tally:
    def __init__(self) -> None:
        self.agent_steps = 0
        self.best_moves = Counter()
        self.non_greedy = Counter()
        self.agree = Counter()
        self.disagree = Counter()
        self.reasons = Counter()
        self.goal_busy = Counter()
        self.off_goal = Counter()
        self.reason_overlap = Counter()
        self.examples = {}
        self.contests = 0
        self.contest_features = defaultdict(Counter)
        self.instances = 0
        self.optimal = 0

    def add_contest(self, feature, winner_value, loser_value):
        if winner_value > loser_value:
            self.contest_features[feature]["winner higher"] += 1
        elif winner_value < loser_value:
            self.contest_features[feature]["winner lower"] += 1
        else:
            self.contest_features[feature]["equal"] += 1


def analyse_instance(grid, starts, goals, configs, dist, seed, tally: Tally):
    agents = range(len(starts))
    solvers = {}
    for name, switches in VARIANTS.items():
        solver = PIBT(grid, starts, goals, seed=seed, dist=dist, **switches)
        solver.reset()
        solvers[name] = solver
    start_distance = [dist.get(i, starts[i]) for i in agents]
    goal_busy_until = [0] * len(starts)
    for t, config in enumerate(configs):
        for other, cell in enumerate(config):
            for i in agents:
                if i != other and cell == goals[i]:
                    goal_busy_until[i] = t

    for t in range(len(configs) - 1):
        config, nxt_config = configs[t], configs[t + 1]
        position_now = {cell: i for i, cell in enumerate(config)}
        pibt_next = {}
        for name, solver in solvers.items():
            solver.current = list(config)
            pibt_next[name] = solver.step()
        priorities = solvers[BASE].priorities

        best_type = [move_type(dist, i, config[i], nxt_config[i]) for i in agents]
        for i in agents:
            tally.agent_steps += 1
            tally.best_moves[best_type[i]] += 1
            if best_type[i] in (CLOSER, WAIT, AWAY):
                tally.off_goal[best_type[i]] += 1
                tally.goal_busy[best_type[i]] += t + dist.get(i, config[i]) <= goal_busy_until[i]
            for name in VARIANTS:
                tally.agree[name] += pibt_next[name][i] == nxt_config[i]

            if best_type[i] in (WAIT, AWAY):
                free = free_closer_cells(grid, dist, i, config, nxt_config, position_now)
                reason = "a closer cell was free" if free else "every closer cell was taken"
                tally.non_greedy[f"{best_type[i]}: {reason}"] += 1
            elif best_type[i] == LEAVE:
                entered = nxt_config.count(config[i]) > 0
                reason = "another agent moves in" if entered else "nobody takes the cell"
                tally.non_greedy[f"{best_type[i]}: {reason}"] += 1

            mine = pibt_next[BASE][i]
            if mine != nxt_config[i]:
                pibt_type = move_type(dist, i, config[i], mine)
                if best_type[i] == CLOSER and pibt_type == CLOSER:
                    label = "both step closer, to different cells"
                else:
                    label = f"best solution {best_type[i]}; PIBT {pibt_type}"
                tally.disagree[label] += 1
                if best_type[i] in (WAIT, AWAY) and pibt_type == CLOSER:
                    later = configs[min(t + 2, len(configs) - 1)]
                    found = why_not_greedy(
                        i,
                        mine,
                        t,
                        config,
                        nxt_config,
                        later,
                        position_now,
                        goals,
                        dist,
                        goal_busy_until,
                    )
                    tally.reasons[(best_type[i], found[0])] += 1
                    for reason in found:
                        tally.reason_overlap[(best_type[i], reason)] += 1
                    key = (best_type[i], found[0])
                    if key not in tally.examples:
                        tally.examples[key] = (
                            len(starts),
                            t,
                            i,
                            config[i],
                            nxt_config[i],
                            mine,
                            goals[i],
                        )

        arrivals = defaultdict(list)
        for i in agents:
            if nxt_config[i] != config[i]:
                arrivals[nxt_config[i]].append(i)
        for cell, movers in arrivals.items():
            winner = movers[0]
            if best_type[winner] != CLOSER:
                continue
            for loser in agents:
                if loser == winner or best_type[loser] not in (WAIT, AWAY):
                    continue
                if cell not in neighbours(grid, config[loser]):
                    continue
                if dist.get(loser, cell) >= dist.get(loser, config[loser]):
                    continue
                tally.contests += 1
                tally.add_contest("PIBT priority", priorities[winner], priorities[loser])
                tally.add_contest(
                    "distance still to go",
                    dist.get(winner, config[winner]),
                    dist.get(loser, config[loser]),
                )
                tally.add_contest(
                    "start-to-goal distance", start_distance[winner], start_distance[loser]
                )
                tally.add_contest(
                    "steps already taken beyond the shortest path",
                    t + dist.get(winner, config[winner]) - start_distance[winner],
                    t + dist.get(loser, config[loser]) - start_distance[loser],
                )
                tally.add_contest(
                    "free neighbouring cells",
                    sum(c not in position_now for c in neighbours(grid, config[winner])),
                    sum(c not in position_now for c in neighbours(grid, config[loser])),
                )


def table(title, counter, total, limit=12):
    lines = [title]
    for label, count in counter.most_common(limit):
        lines.append(f"  {count:9d}  {100 * count / max(total, 1):5.1f}%  {label}")
    return "\n".join(lines)


def report(name, tally: Tally) -> str:
    steps = tally.agent_steps
    out = [
        f"===== {name}: {tally.instances} instances ({tally.optimal} provably optimal), {steps} agent-steps =====",
        table("What the best solution does each agent-step", tally.best_moves, steps),
        table(
            "Non-greedy moves in the best solution, and the situation",
            tally.non_greedy,
            sum(tally.non_greedy.values()),
        ),
        "How often PIBT, placed in the same position, picks the same move",
    ]
    for variant in VARIANTS:
        out.append(f"  {100 * tally.agree[variant] / max(steps, 1):5.1f}%  {variant}")
    out.append(
        table(
            f"Where base PIBT ({BASE} rule) differs, most common first",
            tally.disagree,
            sum(tally.disagree.values()),
        )
    )
    out.append("Share of moves made while the agent's goal is still needed by another agent")
    for kind in (CLOSER, WAIT, AWAY):
        share = 100 * tally.goal_busy[kind] / max(tally.off_goal[kind], 1)
        out.append(f"  {share:5.1f}%  when the best solution {kind}")
    for kind in (WAIT, AWAY):
        first = Counter({r: c for (k, r), c in tally.reasons.items() if k == kind})
        total = sum(first.values())
        out.append(
            table(
                f"Best solution {kind} while PIBT steps closer ({total} cases): first reason that applies",
                first,
                total,
            )
        )
        every = Counter({r: c for (k, r), c in tally.reason_overlap.items() if k == kind})
        out.append(table("  counting every reason that applies (they can overlap)", every, total))
    out.append(
        f"Contested cells: {tally.contests} cases where one agent took a cell another also wanted"
    )
    for feature, counts in tally.contest_features.items():
        decided = counts["winner higher"] + counts["winner lower"]
        share = 100 * counts["winner higher"] / max(decided, 1)
        out.append(
            f"  winner had the higher value in {share:5.1f}% of {decided} decided cases: {feature}"
        )
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare PIBT's one-step choices with best-known plans from the MAPF Tracker."
    )
    parser.add_argument("--maps", nargs="+", default=["empty-8-8", "random-32-32-20"])
    parser.add_argument(
        "--agent-step", type=int, default=10, help="use every k-th agent count on big maps"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="stop after this many instances per map"
    )
    parser.add_argument("--optimal-only", action="store_true", help="skip plans not proven optimal")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "divergence")
    args = parser.parse_args()

    tallies = {}
    skipped = Counter()
    for map_name in args.maps:
        grid = load_map(DATA_DIR / "maps" / f"{map_name}.map")
        tally = tallies[map_name] = Tally()
        for plan_file in sorted(PLAN_DIR.glob(f"{map_name}-*.json")):
            rows = json.loads(plan_file.read_text())
            scen_path = DATA_DIR / "scens" / f"{plan_file.stem}.scen"
            all_starts, all_goals = load_scen(scen_path)
            largest = max(r["agents"] for r in rows)
            full_dist = DistTable(grid, all_goals[:largest])
            for row in rows:
                n = row["agents"]
                if n < 2 or (largest > 40 and n % args.agent_step):
                    continue
                if args.optimal_only and row["lower_cost"] != row["solution_cost"]:
                    continue
                if args.limit and tally.instances >= args.limit:
                    break
                starts, goals = all_starts[:n], all_goals[:n]
                configs = decode_plan(row["solution_plan"], starts, goals)
                if not validate_solution(grid, starts, goals, configs).ok:
                    skipped["plan did not validate"] += 1
                    continue
                if sum_of_costs(configs, goals) != row["solution_cost"]:
                    skipped["cost differs from the tracker's"] += 1
                    continue
                tally.instances += 1
                tally.optimal += row["lower_cost"] == row["solution_cost"]
                seed = derive_seed(plan_file.stem, n)
                analyse_instance(
                    grid, starts, goals, configs, PrefixDist(full_dist, n), seed, tally
                )
        print(report(map_name, tally), flush=True)
        print()

    if skipped:
        print("skipped:", dict(skipped))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "disagreements.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["map", "table", "label", "count"])
        for map_name, tally in tallies.items():
            for label, count in tally.best_moves.most_common():
                writer.writerow([map_name, "best solution move", label, count])
            for label, count in tally.non_greedy.most_common():
                writer.writerow([map_name, "non-greedy move", label, count])
            for label, count in tally.disagree.most_common():
                writer.writerow([map_name, "PIBT differs", label, count])
            for (kind, reason), count in tally.reason_overlap.most_common():
                writer.writerow([map_name, f"why best solution {kind}", reason, count])
            for feature, counts in tally.contest_features.items():
                for outcome, count in counts.items():
                    writer.writerow([map_name, f"contest: {feature}", outcome, count])
    print(f"wrote {args.out / 'disagreements.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
