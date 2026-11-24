import argparse
import csv
from collections import defaultdict
from pathlib import Path

BASELINE = "ours-random"
SWITCH_NAMES = {
    "s1": "hindrance",
    "s2": "weighted choice",
    "s3": "priority swap",
    "s4": "parked-agent rule",
    "s5": "goal look-ahead",
}


def load(folder: Path) -> list[dict]:
    rows = []
    for path in sorted(folder.glob("*.csv")):
        with path.open() as f:
            rows.extend(csv.DictReader(f))
    for row in rows:
        row["success"] = row["success"] == "True"
        row["valid"] = row["valid"] == "True"
        row["cell"] = (row["map_name"], int(row["num_agents"]))
        row["run"] = (row["map_name"], row["scen_name"], row["num_agents"], row["rep"])
        if row["success"]:
            row["cost"] = float(row["sum_of_costs"]) / max(float(row["soc_lower_bound"]), 1.0)
            row["displaced"] = float(row["goal_displacements"])
        row["ms"] = 1000 * float(row["runtime_per_step_s"])
    return rows


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def order(solvers):
    def key(name):
        if name == "ours-paper":
            return (0, 0, name)
        if name == BASELINE:
            return (0, 1, name)
        if name == "pypibt":
            return (0, 2, name)
        return (1, name.count("+"), name)

    return sorted(solvers, key=key)


def switches_of(name):
    return frozenset(name.split("+")) if name.startswith("s") else frozenset()


def paired(by_solver, solver, other, field):
    mine, theirs = by_solver[solver], by_solver[other]
    shared = [
        run for run in mine if run in theirs and mine[run]["success"] and theirs[run]["success"]
    ]
    return mean(mine[r][field] for r in shared), mean(theirs[r][field] for r in shared), len(shared)


def change(new, old):
    return 100 * (new - old) / old if old else float("nan")


def markdown(header, lines):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in line) + " |" for line in lines]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Turn run_compare CSV files into report tables.")
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()

    rows = load(args.folder)
    invalid = [r for r in rows if not r["valid"]]
    by_solver = defaultdict(dict)
    for row in rows:
        by_solver[row["solver"]][row["run"]] = row
    solvers = order(by_solver)
    cells = sorted({r["cell"] for r in rows})
    runs_per_solver = len(by_solver[BASELINE])
    print(
        f"{len(rows)} runs, {len(solvers)} variants, {runs_per_solver} runs per variant, {len(invalid)} invalid solutions\n"
    )

    base_solved = sum(r["success"] for r in by_solver[BASELINE].values())
    base_ms = mean(r["ms"] for r in by_solver[BASELINE].values())
    lines = []
    for solver in solvers:
        mine = by_solver[solver]
        solved = sum(r["success"] for r in mine.values())
        cost, base_cost, shared = paired(by_solver, solver, BASELINE, "cost")
        displaced, base_displaced, _ = paired(by_solver, solver, BASELINE, "displaced")
        ms = mean(r["ms"] for r in mine.values())
        lines.append(
            [
                solver,
                f"{solved}/{len(mine)}",
                f"{100 * solved / len(mine):.1f}%",
                f"{solved - base_solved:+d}",
                f"{cost:.3f}",
                f"{change(cost, base_cost):+.1f}%",
                f"{displaced:.1f}",
                f"{change(displaced, base_displaced):+.0f}%",
                f"{ms:.2f}",
                f"{ms / base_ms:.1f}x",
            ]
        )
    print(
        "Table 1. Every variant against the baseline (random ties), over all maps and agent counts"
    )
    print(
        markdown(
            [
                "Variant",
                "Solved",
                "Success",
                "Runs gained",
                "Cost / LB",
                "Cost change",
                "Displacements",
                "Change",
                "ms/step",
                "Time",
            ],
            lines,
        )
    )
    print(
        "\nCost and displacements are averaged over the runs that both the variant and the baseline solved.\n"
    )

    header = ["Variant"] + [f"{m} ({n})" for m, n in cells] + ["Average"]
    lines = []
    for solver in solvers:
        rates = []
        for cell in cells:
            here = [r for r in by_solver[solver].values() if r["cell"] == cell]
            rates.append(100 * sum(r["success"] for r in here) / len(here))
        lines.append([solver] + [f"{v:.0f}%" for v in rates] + [f"{mean(rates):.1f}%"])
    print("Table 2. Success rate by map and number of agents")
    print(markdown(header, lines))

    lines = []
    for solver in solvers:
        changes = []
        for cell in cells:
            mine = {k: v for k, v in by_solver[solver].items() if v["cell"] == cell}
            theirs = {k: v for k, v in by_solver[BASELINE].items() if v["cell"] == cell}
            cost, base_cost, _ = paired({solver: mine, BASELINE: theirs}, solver, BASELINE, "cost")
            changes.append(change(cost, base_cost))
        lines.append([solver] + [f"{v:+.1f}%" for v in changes] + [f"{mean(changes):+.1f}%"])
    print(
        "\nTable 3. Cost change against the baseline, by map and number of agents (negative is better)"
    )
    print(markdown(header, lines))

    lines = []
    for switch, label in SWITCH_NAMES.items():
        gains, costs, moves, pairs = [], [], [], 0
        for solver in solvers:
            active = switches_of(solver)
            if switch not in active:
                continue
            without = "+".join(sorted(active - {switch})) or BASELINE
            if without not in by_solver:
                continue
            pairs += 1
            gains.append(
                sum(r["success"] for r in by_solver[solver].values())
                - sum(r["success"] for r in by_solver[without].values())
            )
            cost, other_cost, _ = paired(by_solver, solver, without, "cost")
            costs.append(change(cost, other_cost))
            displaced, other_displaced, _ = paired(by_solver, solver, without, "displaced")
            moves.append(change(displaced, other_displaced))
        if pairs:
            lines.append(
                [
                    f"{switch} {label}",
                    pairs,
                    f"{mean(gains):+.1f}",
                    f"{mean(costs):+.1f}%",
                    f"{mean(moves):+.0f}%",
                ]
            )
    print(
        "\nTable 4. Average effect of turning one switch on, over every combination of the others"
    )
    print(
        markdown(
            [
                "Switch",
                "Combinations compared",
                f"Runs gained (of {runs_per_solver})",
                "Cost change",
                "Displacement change",
            ],
            lines,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
