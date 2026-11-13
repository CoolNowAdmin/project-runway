"""Data the Runway interface needs after sign-in: towns and sales (map.json), roads, bus stops and
amenities (features.json), and one Wikimedia Commons photo per town with its credit. The landing page
gets the town list and one photo at a time before that (load_towns, town_photo)."""

from __future__ import annotations

import base64
import csv
import functools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = ROOT / "data" / "game"
PHOTO_DIR = ROOT / "data" / "photos"


@functools.lru_cache(maxsize=1)
def map_data() -> dict:
    """map.json (~2.5 MB), parsed once per process and shared by every reader. Read-only: callers must not change it."""
    return json.loads((GAME_DIR / "map.json").read_text())


@functools.lru_cache(maxsize=1)
def _photo_rows() -> list[dict]:
    with (PHOTO_DIR / "landmarks.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _photo(row: dict) -> dict | None:
    path = PHOTO_DIR / row["photo_file"] if row.get("photo_file") else None
    if path and path.exists():
        return {"img": _data_uri(str(path)), "credit": row["caption"], "landmark": row["landmark"], "url": row["source_url"]}
    return None


@functools.lru_cache(maxsize=64)
def _data_uri(path: str) -> str:
    """Each photo is read and encoded once per process, not on every request (26 towns, ~20 KB each)."""
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def load_photos() -> dict[str, dict]:
    return {row["town"]: photo for row in _photo_rows() if (photo := _photo(row))}


def town_photo(town) -> dict | None:
    """One town's photo. `town` comes from the browser, so it is only compared with the CSV's town column."""
    row = next((r for r in _photo_rows() if r["town"] == town), None)
    return _photo(row) if row else None


@functools.lru_cache(maxsize=1)
def load_towns() -> list[dict]:
    """Each town's lease premium and its number of recent resales, sorted by name. map.json is ~2.5 MB, so once per process."""
    m = map_data()
    n = [0] * len(m["towns"])
    for r in m["recent"]:
        n[r["t"]] += len(r["x"])
    towns = [{"id": t["id"], "name": t["name"], "pct": t["pct"], "low": t["low"], "n": n[i]} for i, t in enumerate(m["towns"])]
    return sorted(towns, key=lambda t: t["name"])


@functools.lru_cache(maxsize=1)
def recent_months() -> list[str]:
    """The months of the map's recent sales ("2026-07", ...), so the page can label the window from the data."""
    m = map_data()
    return sorted({x[0] for r in m["recent"] for x in r["x"]})


def load_game_data() -> dict:
    return {
        "M": map_data(),
        "F": json.loads((GAME_DIR / "features.json").read_text()),
        "PHOTOS": load_photos(),
    }
