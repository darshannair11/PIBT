import argparse
import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "tracker_plans"
API = "https://fe2410d1.pathfinding.ai/api"
HEADERS = {"Content-Type": "application/json", "User-Agent": "mapf-course-project"}


def get_json(path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download best-known plans from the MAPF Tracker.")
    parser.add_argument("--maps", nargs="+", default=["empty-8-8", "random-32-32-20"])
    parser.add_argument("--max-agents", type=int, default=120)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = [s for s in get_json("/scenario") if s["map_name"] in args.maps]
    for scenario in sorted(scenarios, key=lambda s: (s["map_name"], s["scen_type"], s["type_id"])):
        name = f"{scenario['map_name']}-{scenario['scen_type']}-{scenario['type_id']}"
        out_path = OUT_DIR / f"{name}.json"
        if out_path.exists():
            continue
        body = {"scenario": scenario["id"], "solutions": True, "limit": args.max_agents, "skip": 0}
        rows = [r for r in get_json("/bulk/results", body) if r["agents"] <= args.max_agents]
        out_path.write_text(json.dumps(rows))
        print(f"{name}: {len(rows)} instances")
        time.sleep(0.3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
