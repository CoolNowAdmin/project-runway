"""Monthly data refresh: download HDB's five resale CSVs from data.gov.sg, rebuild the dataset, and update the
figures the interface states as text.

Usage:
    python scripts/refresh_data.py [download-folder]      (default: a temporary folder)

Steps: download (stdlib urllib only) -> scripts/build_dataset.py (data/resale.parquet, data/dataset_meta.json)
-> rewrite the dataset's size and span in runway_game/index.html (landing stats, Sources, How it works).
Trends and the lease premium are worked out from resale.parquet when the app runs, so they follow on their own.

Not refreshed: data/game/map.json and data/game/features.json (the map's geocoded sales, blocks, roads, MRT,
amenities and each town's lease effect). They came from the design hand-off without a script, so the map keeps
its own window (labelled from map.json) while Trends runs to the latest month (labelled from resale.parquet).
"""

from __future__ import annotations

import calendar
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "runway_game" / "index.html"
API = "https://api-open.data.gov.sg/v1/public/api/datasets/{}/{}"
# data.gov.sg collection 189 "Resale Flat Prices", child datasets (checked against the collection's metadata, Nov 2026).
# File names keep "1990"/"2000" for the approval-date files, which build_dataset.py looks for.
DATASETS = {
    "resale-1990-1999.csv": "d_ebc5ab87086db484f88045b47411ebc5",  # based on approval date
    "resale-2000-feb2012.csv": "d_43f493c6c50d54243cc1eab0df142d6a",  # based on approval date
    "resale-mar2012-dec2014.csv": "d_2d5ff9ea31397b66239f245f57751537",
    "resale-jan2015-dec2016.csv": "d_ea9ed51da2787afaf8e51f827c304208",
    "resale-jan2017-onwards.csv": "d_8b84c4ee58e3cfc0ece0d773c8ca6abc",
}
COLUMNS = {"month", "town", "flat_type", "storey_range", "floor_area_sqm", "flat_model", "lease_commence_date", "resale_price"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "runway-data-refresh"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def api(dataset_id: str, action: str) -> dict:
    body = json.loads(fetch(API.format(dataset_id, action)))
    if body.get("code") != 0:
        raise RuntimeError(f"{dataset_id} {action}: {body.get('errorMsg') or body}")
    return body.get("data") or {}


def csv_url(dataset_id: str, polls: int = 20, wait: float = 3.0) -> str:
    """data.gov.sg prepares the file, then a poll returns a short-lived download link."""
    api(dataset_id, "initiate-download")
    for _ in range(polls):
        data = api(dataset_id, "poll-download")
        if data.get("status") == "DOWNLOAD_SUCCESS" and data.get("url"):
            return data["url"]
        time.sleep(wait)
    raise RuntimeError(f"{dataset_id}: download not ready after {polls} polls")


def download(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, dataset_id in DATASETS.items():
        body = fetch(csv_url(dataset_id))
        header = set(body.split(b"\n", 1)[0].decode("utf-8-sig").strip().split(","))
        if missing := COLUMNS - header:  # an error page or a changed schema must not reach the build
            raise RuntimeError(f"{name}: not the resale CSV (missing {sorted(missing)})")
        (folder / name).write_bytes(body)
        print(f"{name}: {len(body):,} bytes")


def page_figures(meta: dict) -> list[str]:
    """The dataset's size and span exactly as the interface writes them (tests/test_app.py checks the same)."""
    y0, y1, mon = meta["first_month"][:4], meta["last_month"][:4], calendar.month_abbr[int(meta["last_month"][5:])]
    return [f"{meta['rows']:,}", f"<b>{y0}–{y1}</b>", f"from {y0} to {mon} {y1}", f"{y0} – {mon} {y1} ("]


def update_page(old: dict, new: dict, page: Path = PAGE) -> None:
    text = page.read_text(encoding="utf-8")
    for a, b in zip(page_figures(old), page_figures(new)):
        if a not in text:
            raise RuntimeError(f"{page.name} no longer says {a!r}; update page_figures()")
        text = text.replace(a, b)
    page.write_text(text, encoding="utf-8")


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="resale-"))
    old = json.loads((build_dataset.OUT_DIR / "dataset_meta.json").read_text())
    download(folder)
    sys.argv = ["build_dataset.py", str(folder)]
    build_dataset.main()
    update_page(old, json.loads((build_dataset.OUT_DIR / "dataset_meta.json").read_text()))


if __name__ == "__main__":
    main()
