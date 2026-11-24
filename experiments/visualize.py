import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mapf.grid import Instance, load_instance, parse_map  # noqa: E402
from mapf.pibt import PIBT, TIE_BREAK_RULES, TIE_PAPER  # noqa: E402

PRESETS = {
    "push": {
        "title": "Priority inheritance: the blocked agent is pushed round the loop",
        "map": "..\n..",
        "starts": [(0, 0), (0, 1)],
        "goals": [(0, 1), (0, 0)],
        "seed": 0,
        "steps": 12,
    },
    "displace": {
        "title": "An agent resting on its goal is pushed off, then comes back",
        "map": ".....\n.....\n.....",
        "starts": [(1, 0), (1, 2)],
        "goals": [(1, 4), (1, 2)],
        "seed": 0,
        "steps": 12,
    },
    "backtrack": {
        "title": "Backtracking: the push fails at a dead end, so the pusher gives up",
        "map": "...",
        "starts": [(0, 0), (0, 1)],
        "goals": [(0, 2), (0, 1)],
        "seed": 0,
        "steps": 8,
    },
    "dead_end": {
        "title": "Fault: two agents frozen at a dead-end pocket",
        "map": "@@.\n...\n@.@",
        "starts": [(1, 0), (2, 1)],
        "goals": [(2, 1), (1, 1)],
        "seed": 0,
        "steps": 20,
    },
    "ping_pong": {
        "title": "Fault: two agents shuttle up and down a corridor forever",
        "map": ".@.\n...\n..@\n@.@\n...\n..@",
        "starts": [(4, 1), (3, 1), (0, 2), (1, 2), (2, 0)],
        "goals": [(2, 1), (3, 1), (0, 2), (1, 2), (2, 0)],
        "seed": 0,
        "steps": 30,
    },
}


class TracedPIBT(PIBT):
    def step(self):
        self.calls = []
        self.step_priorities = []
        return super().step()

    def plan_step(self, state):
        self.step_priorities = [round(p, 2) for p in state.priorities]
        return super().plan_step(state)

    def _pibt(self, agent, caller, state, depth=1):
        record = {"agent": agent, "caller": caller, "depth": depth}
        self.calls.append(record)
        valid = super()._pibt(agent, caller, state, depth)
        record["valid"] = valid
        record["cell"] = list(state.nxt[agent])
        return valid


def run_trace(instance: Instance, seed: int, tie_break: str, max_steps: int) -> dict:
    solver = TracedPIBT(
        instance.grid, instance.starts, instance.goals, seed=seed, tie_break=tie_break
    )
    solver.reset()
    goals = list(instance.goals)
    frames = [{"positions": [list(c) for c in solver.current], "priorities": [], "calls": []}]
    while solver.current != goals and len(frames) <= max_steps:
        solver.step()
        frames.append(
            {
                "positions": [list(c) for c in solver.current],
                "priorities": solver.step_priorities,
                "calls": solver.calls,
            }
        )
    return {
        "free": [[bool(v) for v in row] for row in instance.grid.free],
        "goals": [list(c) for c in goals],
        "frames": frames,
        "solved": solver.current == goals,
        "seed": seed,
        "tie_break": tie_break,
    }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PIBT step by step</title>
<style>
  :root { --bg:#fafafa; --panel:#ffffff; --ink:#1c1c1c; --muted:#6b6b6b; --line:#d9d9d9; --wall:#3a3a3a; --bad:#c62828; --good:#2e7d32; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#161616; --panel:#1f1f1f; --ink:#ececec; --muted:#a0a0a0; --line:#3a3a3a; --wall:#0a0a0a; --bad:#ef6b6b; --good:#7bc67e; }
  }
  * { box-sizing: border-box; }
  body { margin:0; padding:16px; background:var(--bg); color:var(--ink); font:15px/1.45 system-ui, sans-serif; }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { color:var(--muted); margin:0 0 12px; }
  .layout { display:flex; flex-wrap:wrap; gap:16px; align-items:flex-start; }
  .board { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }
  canvas { display:block; max-width:100%; }
  .side { flex:1 1 320px; min-width:280px; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }
  .controls { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:10px; }
  button { font:inherit; padding:6px 12px; border:1px solid var(--line); border-radius:6px; background:var(--panel); color:var(--ink); cursor:pointer; }
  button:hover { border-color:var(--muted); }
  input[type=range] { flex:1 1 140px; }
  .status { font-weight:600; margin-bottom:8px; }
  .log { margin:0; padding:0; list-style:none; max-height:52vh; overflow:auto; }
  .log li { padding:3px 0; border-bottom:1px dashed var(--line); }
  .bad { color:var(--bad); font-weight:600; }
  .good { color:var(--good); }
  .dot { display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:5px; vertical-align:-1px; }
  .legend { color:var(--muted); font-size:13px; margin-top:10px; }
  .note { margin-top:10px; padding:8px 10px; border-left:3px solid var(--bad); background:rgba(198,40,40,.08); display:none; }
</style>
</head>
<body>
<h1 id="title"></h1>
<p class="sub" id="sub"></p>
<div class="layout">
  <div class="board">
    <canvas id="grid"></canvas>
    <div class="controls">
      <button id="prev">Back</button>
      <button id="play">Play</button>
      <button id="next">Next</button>
      <input id="slider" type="range" min="0" value="0">
      <span id="counter"></span>
    </div>
    <div class="legend">Circle = agent. Small square = that agent's goal. Ring = agent is on its goal. Arrow = the move made in this step.</div>
  </div>
  <div class="side">
    <div class="status" id="status"></div>
    <ul class="log" id="log"></ul>
    <div class="note" id="note"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const TITLE = __TITLE__;
const frames = DATA.frames, goals = DATA.goals, free = DATA.free;
const rows = free.length, cols = free[0].length, n = goals.length;
const cell = Math.max(14, Math.min(72, Math.floor(Math.min(640 / cols, 560 / rows))));
const canvas = document.getElementById("grid"), ctx = canvas.getContext("2d");
const ratio = window.devicePixelRatio || 1;
canvas.width = cols * cell * ratio; canvas.height = rows * cell * ratio;
canvas.style.width = cols * cell + "px"; canvas.style.height = rows * cell + "px";
ctx.scale(ratio, ratio);
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const colour = i => "hsl(" + Math.round((i * 360 / Math.max(n, 1) + 200) % 360) + " 65% 50%)";
const same = (a, b) => a[0] === b[0] && a[1] === b[1];
let current = 0, timer = null, tweenStart = 0;

document.getElementById("title").textContent = TITLE;
document.getElementById("sub").textContent = n + " agents, tie-break rule: " + DATA.tie_break + ", seed " + DATA.seed +
  ". Result: " + (DATA.solved ? "solved in " + (frames.length - 1) + " steps." : "not solved within " + (frames.length - 1) + " steps.");
const slider = document.getElementById("slider");
slider.max = frames.length - 1;

function draw(progress) {
  const now = frames[current].positions, before = current > 0 ? frames[current - 1].positions : now;
  ctx.clearRect(0, 0, cols * cell, rows * cell);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    ctx.fillStyle = free[r][c] ? css("--panel") : css("--wall");
    ctx.fillRect(c * cell, r * cell, cell, cell);
    ctx.strokeStyle = css("--line"); ctx.lineWidth = 1;
    ctx.strokeRect(c * cell + .5, r * cell + .5, cell - 1, cell - 1);
  }
  const g = cell * 0.26;
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = colour(i); ctx.globalAlpha = .55;
    ctx.fillRect(goals[i][1] * cell + cell - g - 3, goals[i][0] * cell + 3, g, g);
    ctx.globalAlpha = 1;
  }
  for (let i = 0; i < n; i++) {
    const y = (before[i][0] + (now[i][0] - before[i][0]) * progress + .5) * cell;
    const x = (before[i][1] + (now[i][1] - before[i][1]) * progress + .5) * cell;
    if (!same(before[i], now[i])) {
      ctx.strokeStyle = colour(i); ctx.lineWidth = Math.max(2, cell / 14); ctx.globalAlpha = .45;
      ctx.beginPath(); ctx.moveTo((before[i][1] + .5) * cell, (before[i][0] + .5) * cell); ctx.lineTo(x, y); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.fillStyle = colour(i);
    ctx.beginPath(); ctx.arc(x, y, cell * .3, 0, Math.PI * 2); ctx.fill();
    if (same(now[i], goals[i]) && progress === 1) {
      ctx.strokeStyle = css("--ink"); ctx.lineWidth = Math.max(2, cell / 16);
      ctx.beginPath(); ctx.arc(x, y, cell * .38, 0, Math.PI * 2); ctx.stroke();
    }
    if (cell >= 22) {
      ctx.fillStyle = "#fff"; ctx.font = "600 " + Math.round(cell * .3) + "px system-ui"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(i, x, y + 1);
    }
  }
}

function tag(i) { return '<span class="dot" style="background:' + colour(i) + '"></span>agent ' + i; }
function at(c) { return "(" + c[0] + ", " + c[1] + ")"; }

function describe() {
  const frame = frames[current], log = document.getElementById("log"), note = document.getElementById("note");
  document.getElementById("counter").textContent = "step " + current + " / " + (frames.length - 1);
  slider.value = current;
  note.style.display = "none";
  if (current === 0) {
    document.getElementById("status").textContent = "Start positions";
    log.innerHTML = "<li>Every agent starts with a small random priority between 0 and 1.</li>";
    return;
  }
  const before = frames[current - 1].positions, now = frame.positions;
  const onGoal = now.filter((p, i) => same(p, goals[i])).length;
  document.getElementById("status").textContent = "Step " + current + ": " + onGoal + " of " + n + " agents on their goal";
  const order = [...Array(n).keys()].sort((a, b) => frame.priorities[b] - frame.priorities[a]);
  let html = "<li>Priority order this step: " + order.slice(0, 8).map(i => tag(i) + " (" + frame.priorities[i].toFixed(2) + ")").join(", ") + (n > 8 ? ", ..." : "") + "</li>";
  for (const call of frame.calls) {
    const i = call.agent, pad = "&nbsp;".repeat((call.depth - 1) * 5);
    const moved = !same(before[i], call.cell);
    const wasOnGoal = same(before[i], goals[i]);
    let line = pad;
    line += call.caller === null ? tag(i) + " chooses" : "&#8627; pushed by agent " + call.caller + ", " + tag(i);
    if (call.valid) line += moved ? ' <span class="good">moves to ' + at(call.cell) + "</span>" : " stays at " + at(call.cell);
    else line += ' <span class="bad">has nowhere to go and stays (push fails)</span>';
    if (moved && wasOnGoal) line += ' <span class="bad">&mdash; pushed off its goal</span>';
    html += "<li>" + line + "</li>";
  }
  log.innerHTML = html;
  if (current === frames.length - 1 && !DATA.solved) {
    const stuck = now.map((p, i) => same(p, goals[i]) ? -1 : i).filter(i => i >= 0);
    const frozen = current > 4 && stuck.every(i => same(frames[current - 4].positions[i], now[i]));
    note.innerHTML = "Not solved. Agents still off their goal: " + stuck.join(", ") + ". " +
      (frozen ? "They have stopped moving: each one blocks the only cell the other needs." : "They are still moving, repeating the same pattern without ever settling.");
    note.style.display = "block";
  }
}

function show(index, animate) {
  current = Math.max(0, Math.min(frames.length - 1, index));
  describe();
  if (!animate) { draw(1); return; }
  tweenStart = performance.now();
  const tick = t => { const p = Math.min(1, (t - tweenStart) / 260); draw(p); if (p < 1) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}
function stop() { clearInterval(timer); timer = null; document.getElementById("play").textContent = "Play"; }
document.getElementById("next").onclick = () => { stop(); show(current + 1, true); };
document.getElementById("prev").onclick = () => { stop(); show(current - 1, false); };
slider.oninput = () => { stop(); show(+slider.value, false); };
document.getElementById("play").onclick = () => {
  if (timer) { stop(); return; }
  if (current === frames.length - 1) show(0, false);
  document.getElementById("play").textContent = "Pause";
  timer = setInterval(() => { if (current >= frames.length - 1) stop(); else show(current + 1, true); }, 650);
};
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") { stop(); show(current + 1, true); }
  if (e.key === "ArrowLeft") { stop(); show(current - 1, false); }
});
show(0, false);
</script>
</body>
</html>
"""


def write_page(trace: dict, title: str, out_path: Path) -> None:
    page = PAGE.replace("__DATA__", json.dumps(trace)).replace("__TITLE__", json.dumps(title))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Write an HTML page that replays a PIBT run step by step."
    )
    parser.add_argument("--preset", choices=sorted(PRESETS), help="a small hand-made example")
    parser.add_argument("--all", action="store_true", help="write one page per preset")
    parser.add_argument("-m", "--map-file")
    parser.add_argument("-i", "--scen-file")
    parser.add_argument("-N", "--num-agents", type=int)
    parser.add_argument("-s", "--seed", type=int)
    parser.add_argument("--tie-break", choices=TIE_BREAK_RULES, default=TIE_PAPER)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    jobs = []
    if args.all:
        jobs = sorted(PRESETS)
    elif args.preset:
        jobs = [args.preset]

    out_dir = REPO_ROOT / "results" / "visuals"
    for name in jobs:
        preset = PRESETS[name]
        instance = Instance(parse_map(preset["map"], name), preset["starts"], preset["goals"], name)
        seed = preset["seed"] if args.seed is None else args.seed
        trace = run_trace(instance, seed, args.tie_break, args.steps or preset["steps"])
        out_path = args.out if (args.out and len(jobs) == 1) else out_dir / f"{name}.html"
        write_page(trace, preset["title"], out_path)
        print(
            f"{name}: {'solved' if trace['solved'] else 'not solved'} in {len(trace['frames']) - 1} steps -> {out_path}"
        )

    if not jobs:
        if not (args.map_file and args.scen_file and args.num_agents):
            parser.error("give --preset, --all, or all of --map-file, --scen-file and --num-agents")
        instance = load_instance(args.map_file, args.scen_file, args.num_agents)
        seed = 0 if args.seed is None else args.seed
        trace = run_trace(instance, seed, args.tie_break, args.steps or 300)
        out_path = args.out or out_dir / f"{Path(args.scen_file).stem}-{args.num_agents}.html"
        title = f"{Path(args.map_file).stem}, {args.num_agents} agents"
        write_page(trace, title, out_path)
        print(
            f"{'solved' if trace['solved'] else 'not solved'} in {len(trace['frames']) - 1} steps -> {out_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
