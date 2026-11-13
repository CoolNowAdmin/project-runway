"""Price check (runway/price_check.py) and the resale exit view (cpf_rules.resale_exit and its JS twin)."""

import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from runway import price_check as pc
from runway.bridge import handle
from runway.cpf_rules import resale_exit

ROOT = Path(__file__).resolve().parent.parent
GAME = (ROOT / "runway_game" / "index.html").read_text(encoding="utf-8")
NODE = shutil.which("node") or str(Path.home() / ".local/bin/node")
needs_node = pytest.mark.skipif(not (shutil.which("node") or Path(NODE).exists()), reason="needs Node.js")
FLAT = {"town": "TAMPINES", "st": "Tampines St 81", "ft": "4-room", "sqm": 100.0, "lease": 60.0, "price": 600_000}


def sale(psm, street=None, lease=60.0, town="TAMPINES", ft="4 ROOM", month="2026-08", sqm=100.0):
    return {"town": town, "street": street, "month": month, "flat_type": ft, "sqm": sqm,
            "price": psm * sqm, "lease": lease, "psm": psm}


def frame(rows):
    return pd.DataFrame(rows)


def test_town_median_when_the_street_is_thin():
    rows = [sale(5000 + 100 * i, month=f"2026-0{i + 1}") for i in range(7)] + [sale(9000, "Tampines St 81")]
    out = pc.compare(frame(rows), FLAT)
    assert out["level"] == "town" and out["n"] == 8 and out["enough"]
    assert out["typical_psm"] == 5350 and out["psm"] == 6000
    assert out["pct"] == 12 and out["verdict"] == "above"
    assert (out["first"], out["last"]) == ("2026-01", "2026-08")


def test_same_street_wins_with_enough_sales():
    rows = [sale(6100, "Tampines St 81") for _ in range(5)] + [sale(4000) for _ in range(20)]
    out = pc.compare(frame(rows), FLAT)
    assert out["level"] == "street" and out["n"] == 5 and out["verdict"] == "in line" and out["pct"] == -2


def test_like_with_like_only():
    rows = ([sale(6000)] * 3
            + [sale(1000, lease=66), sale(1000, lease=54)]  # outside the 5-year lease band
            + [sale(1000, ft="5 ROOM"), sale(1000, town="BEDOK")]
            + [sale(6000, "Tampines St 81")])  # the flat's own sale: same street, size and price
    out = pc.compare(frame(rows), FLAT)
    assert out["n"] == 3 and not out["enough"]
    assert "typical_psm" not in out and "verdict" not in out  # too few: no number at all


def test_lease_band_edges_count():
    rows = [sale(5000, lease=55), sale(5000, lease=65)] * 3
    out = pc.compare(frame(rows), FLAT)
    assert out["n"] == 6 and (out["lease_from"], out["lease_to"]) == (55, 65) and out["verdict"] == "above"


@pytest.fixture
def fake_sales(monkeypatch):
    monkeypatch.setattr(pc, "sales", lambda: frame([sale(6000)] * 6))


def send(payload):
    return handle({"id": "x", "type": "price_check", "payload": payload}, {}, {}, None, None)


def test_bridge_answers_a_good_flat(fake_sales):
    r = send(FLAT)
    assert r["ok"] and r["verdict"] == "in line" and r["typical_psm"] == 6000


@pytest.mark.parametrize("bad", [
    {"town": "ATLANTIS"}, {"town": ["TAMPINES"]}, {"ft": "penthouse"}, {"ft": None},
    {"sqm": True}, {"sqm": "100"}, {"sqm": 5}, {"lease": 120}, {"lease": float("nan")}, {"price": -1}, {"price": None},
])
def test_bridge_refuses_bad_payloads(fake_sales, bad):
    assert send({**FLAT, **bad}) == {"ok": False, "error": "bad flat"}


def test_bridge_refuses_a_missing_payload(fake_sales):
    assert send("TAMPINES") == {"ok": False, "error": "bad flat"}


def test_bridge_reports_a_data_failure(monkeypatch):
    def broken():
        raise OSError("no parquet")

    monkeypatch.setattr(pc, "sales", broken)
    assert send(FLAT) == {"ok": False, "error": "OSError: no parquet"}


def test_real_data_window_and_streets():
    d = pc.sales()
    months = sorted(d["month"].unique())
    assert len(months) == pc.WINDOW_MONTHS
    assert d.loc[d["month"] >= "2026-07", "street"].notna().all()  # map.json's months carry streets
    assert set(d["flat_type"]) >= {"3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"}


def test_browser_sends_only_public_flat_fields():
    line = next(x for x in GAME.splitlines() if "RW.send('price_check'" in x)
    assert "{town:f.town,st:f.st,ft:f.ft,sqm:f.sqm,lease:f.lease,price:f.price}" in line
    assert "S.age" not in line and "S.oa" not in line
    assert "Nothing you typed goes with it" in GAME


@needs_node
def test_resale_exit_matches_python(tmp_path):
    code = next(x for x in GAME.splitlines() if x.startswith("function resaleExit("))
    cases = [(lease, yrs, age) for lease in (20.5, 35, 44.9, 58.75, 66.6, 80, 95) for yrs in (5, 10, 15, 20)
             for age in (21, 30, 45, 70)]
    js = tmp_path / "exit.js"
    js.write_text(f"{code}\nconsole.log(JSON.stringify({json.dumps(cases)}.map(([l,y,a])=>resaleExit(l,y,a))))")
    got = json.loads(subprocess.run([NODE, str(js)], capture_output=True, text=True, check=True).stdout)
    for (lease, yrs, age), g in zip(cases, got):
        left, full_age, check = resale_exit(lease, yrs, age)
        assert g["left"] == pytest.approx(left) and g["full"] == pytest.approx(full_age)
        assert g["share"] == pytest.approx(check.cpf_share) and g["ltv"] == pytest.approx(check.ltv_share), (lease, yrs, age)


def test_resale_exit_rule():
    assert resale_exit(66, 5, 30)[:2] == (61, 34)  # full CPF needs a buyer of 34 or older
    left, _, check = resale_exit(40, 20, 30)
    assert left == 20 and check.cpf_share == 0 and check.ltv_share == 0  # 20 years or less: no CPF, no HDB loan
    assert resale_exit(10, 20, 30)[0] == 0
