"""EXTRA. Download MovingAI MAPF benchmark maps and scenario files into data/.

Source: https://movingai.com/benchmarks/mapf/index.html (Stern et al., SoCS
2019). Each map has 25 "random" and 25 "even" scenario files:
    random: starts and goals placed uniformly at random;
    even:   agents in buckets of 10 with similar start-goal distance, so short
            and long trips are evenly mixed.

Files go to data/maps/<map>.map and data/scens/<map>-<type>-<id>.scen, the
names run_compare.py and the extras already expect. Existing files are left
alone. Only .map and .scen members are taken from the zips, by base name, so
nothing from an archive can be written outside data/.

Examples:
    python experiments/extras/fetch_movingai.py                       # defaults below
    python experiments/extras/fetch_movingai.py --maps maze-32-32-4 --types random
"""

from __future__ import annotations

import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
BASE_URL = "https://movingai.com/benchmarks/mapf"

# The two maps already used, the four named in README.md, and two maps with
# narrow corridors (maze, room) where plain PIBT is expected to get stuck.
DEFAULT_MAPS = [
    "empty-8-8",
    "random-32-32-20",
    "warehouse-20-40-10-2-2",
    "den520d",
    "ost003d",
    "Paris_1_256",
    "room-32-32-4",
    "maze-32-32-4",
]
SCEN_TYPES = ("random", "even")


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "mapf-benchmark-fetch"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _extract(blob: bytes, suffix: str, out_dir: Path) -> list[Path]:
    """Write every member ending in suffix to out_dir under its base name."""
    written = []
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for member in archive.namelist():
            name = Path(member).name
            if not name.endswith(suffix) or name.startswith("."):
                continue
            target = out_dir / name
            if target.exists():
                continue
            target.write_bytes(archive.read(member))
            written.append(target)
    return written


def fetch(map_name: str, scen_types: list[str]) -> None:
    maps_dir, scens_dir = DATA_DIR / "maps", DATA_DIR / "scens"
    maps_dir.mkdir(parents=True, exist_ok=True)
    scens_dir.mkdir(parents=True, exist_ok=True)

    if (maps_dir / f"{map_name}.map").exists():
        print(f"{map_name}.map: already present")
    else:
        got = _extract(_download(f"{BASE_URL}/{map_name}.map.zip"), ".map", maps_dir)
        print(f"{map_name}.map: {'downloaded' if got else 'NOT FOUND in archive'}")

    for scen_type in scen_types:
        if len(list(scens_dir.glob(f"{map_name}-{scen_type}-*.scen"))) >= 25:
            print(f"{map_name} {scen_type} scenarios: already present")
            continue
        got = _extract(
            _download(f"{BASE_URL}/{map_name}.map-scen-{scen_type}.zip"), ".scen", scens_dir
        )
        print(f"{map_name} {scen_type} scenarios: {len(got)} new files")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--maps", nargs="+", default=DEFAULT_MAPS)
    parser.add_argument("--types", nargs="+", choices=SCEN_TYPES, default=list(SCEN_TYPES))
    args = parser.parse_args(argv)
    for map_name in args.maps:
        fetch(map_name, args.types)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
