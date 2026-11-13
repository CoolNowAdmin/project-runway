"""Price check for one flat on the map: is its price per sqm in line with similar recent sales?

Data: HDB resale prices (data.gov.sg) in data/resale.parquet. The parquet has no street names, so the latest
months come from data/game/map.json instead, which holds the same sales (Jul-Sep 2026) with their streets.
Like with like: same town and flat type, remaining lease within LEASE_BAND years, the latest WINDOW_MONTHS
months. Same street when it has MIN_SALES such sales, otherwise the whole town. Never the flat's own sale.
"""

from __future__ import annotations

import functools
import json
from numbers import Real

import pandas as pd

from runway.game_data import GAME_DIR
from runway.trends import PARQUET

WINDOW_MONTHS = 12
LEASE_BAND = 5  # years either side: lease moves price strongly (see Trends' lease chart)
MIN_SALES = 5  # fewer than this and a median says little
IN_LINE_PCT = 5  # Runway's own cut-off for "in line", not an official figure


def _type(name: str) -> str:
    return name.upper().replace("-", " ")  # map.json "4-room" -> parquet "4 ROOM"


@functools.lru_cache(maxsize=1)
def sales() -> pd.DataFrame:
    """The latest WINDOW_MONTHS of sales: one row each, with the street where map.json has it."""
    m = json.loads((GAME_DIR / "map.json").read_text())
    rows = [{"town": m["towns"][b["t"]]["id"], "street": b["s"], "month": x[0], "flat_type": _type(x[1]),
             "sqm": float(x[3]), "price": float(x[4]), "lease": float(x[5])} for b in m["recent"] for x in b["x"]]
    recent = pd.DataFrame(rows)
    d = pd.read_parquet(PARQUET, columns=["month", "town", "flat_type", "floor_area_sqm", "resale_price", "remaining_lease"])
    month = d["month"].dt.strftime("%Y-%m")
    first = (d["month"].max() - pd.DateOffset(months=WINDOW_MONTHS - 1)).strftime("%Y-%m")
    older = d[((month >= first) & (month < recent["month"].min())).to_numpy()]  # map.json covers the rest
    older = pd.DataFrame({"town": older["town"].astype(str).str.upper().str.replace(" / ", "/").to_numpy(),
                          "street": None, "month": month[older.index].to_numpy(),
                          "flat_type": older["flat_type"].astype(str).to_numpy(), "sqm": older["floor_area_sqm"].to_numpy(float),
                          "price": older["resale_price"].to_numpy(float), "lease": older["remaining_lease"].to_numpy(float)})
    out = pd.concat([older, recent], ignore_index=True)
    out["psm"] = out["price"] / out["sqm"]
    return out


def _number(v, lo: float, hi: float) -> float:
    if not isinstance(v, Real) or isinstance(v, bool) or not lo <= v <= hi:
        raise ValueError("bad number")
    return float(v)


def compare(df: pd.DataFrame, payload: dict) -> dict:
    """Validate the browser's flat (it is untrusted), then compare it with similar sales in df."""
    town, ft, street = payload.get("town"), payload.get("ft"), payload.get("st")
    if not isinstance(town, str) or town not in set(df["town"]):
        raise ValueError("unknown town")
    if not isinstance(ft, str) or _type(ft[:20]) not in set(df["flat_type"]):
        raise ValueError("unknown flat type")
    street = street[:60] if isinstance(street, str) else ""
    sqm, lease, price = _number(payload.get("sqm"), 20, 400), _number(payload.get("lease"), 0, 99), _number(payload.get("price"), 1e4, 1e8)

    near = df[(df["town"] == town) & (df["flat_type"] == _type(ft)) & ((df["lease"] - lease).abs() <= LEASE_BAND)]
    own = near.index[(near["street"] == street) & (near["sqm"] == sqm) & (near["price"] == price)]
    near = near.drop(own[:1])  # the flat's own sale is on the map; it can't be its own yardstick
    same_street = near[near["street"] == street]
    level, pool = ("street", same_street) if len(same_street) >= MIN_SALES else ("town", near)
    out = {"level": level, "n": len(pool), "months": WINDOW_MONTHS, "band": LEASE_BAND,
           "lease_from": max(0, round(lease) - LEASE_BAND), "lease_to": min(99, round(lease) + LEASE_BAND),
           "first": min(pool["month"], default=None), "last": max(pool["month"], default=None), "enough": len(pool) >= MIN_SALES}
    if out["enough"]:
        typical, psm = float(pool["psm"].median()), price / sqm
        pct = round((psm - typical) / typical * 100)
        out.update(typical_psm=round(typical), psm=round(psm), pct=pct,
                   verdict="in line" if abs(pct) <= IN_LINE_PCT else "above" if pct > 0 else "below")
    return out


def price_check(payload: dict) -> dict:
    return compare(sales(), payload)
