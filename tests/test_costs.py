"""Upfront cost and loan comparison: runway/costs.py against the corpus, and index.html against costs.py."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from runway.costs import grants, hdb_fees, loan_for_instalment, loan_options, stamp_duty
from runway.cpf_rules import flat_money, monthly_instalment

ROOT = Path(__file__).resolve().parents[1]
GAME = (ROOT / "runway_game" / "index.html").read_text()
NODE = shutil.which("node") or str(Path.home() / ".local/bin/node")


def test_stamp_duty_matches_iras_example():
    # iras-buyers-stamp-duty.md, Example 1: $4,500,100 -> $209,606
    assert stamp_duty(4_500_100) == 209_606
    # band edges: first $180,000 at 1%, next $180,000 at 2%, next $640,000 at 3%
    assert stamp_duty(180_000) == 1_800
    assert stamp_duty(360_000) == 5_400
    assert stamp_duty(500_000) == 9_600
    assert stamp_duty(1_000_000) == 24_600
    assert stamp_duty(0) == 0


def test_hdb_fees():
    # hdb-mode-of-financing-resale.md: $120 Request for Value + $80 resale fee ($40 for 1- and 2-room)
    assert hdb_fees("4-room") == 200 and hdb_fees("2-room") == 160 and hdb_fees("Executive") == 200


def test_family_grants():
    g = grants("4-room", 70, 8_000, "family", "first", "sc", "with")
    assert g == {"chg": 80_000, "ehg_max": 120_000, "phg": 30_000}  # $230,000 max, mynicehome-grants-guide.md
    assert grants("5-room", 70, 8_000, "family", "first", "spr", "near") == {"chg": 40_000, "ehg_max": 120_000, "phg": 20_000}
    assert grants("4-room", 70, 9_001, "family", "first")["ehg_max"] == 0  # EHG ceiling $9,000
    assert grants("4-room", 70, 16_001, "family", "first")["chg"] == 0  # CPF Housing Grant ceiling $16,000
    assert grants("3-room", 70, 9_000, "family", "mixed") == {"chg": 40_000, "ehg_max": 60_000, "phg": 0}
    assert grants("Executive", 70, 9_001, "family", "mixed") == {"chg": 25_000, "ehg_max": 0, "phg": 0}
    assert grants("4-room", 70, 5_000, "family", "no", parents="near") == {"chg": 0, "ehg_max": 0, "phg": 20_000}
    assert grants("4-room", 20, 5_000, "family", "first", parents="with") == {"chg": 0, "ehg_max": 0, "phg": 0}
    assert grants("1-room", 70, 5_000, "family", "first")["chg"] == 0


def test_single_grants():
    # mynicehome-grants-guide.md: singles up to $115,000 = 40,000 + 60,000 + 15,000
    assert grants("4-room", 70, 4_000, "single", "first", parents="with") == {"chg": 40_000, "ehg_max": 60_000, "phg": 15_000}
    assert grants("5-room", 70, 6_000, "single", "first", parents="near") == {"chg": 25_000, "ehg_max": 0, "phg": 10_000}
    assert grants("Executive", 70, 4_000, "single", "first")["chg"] == 0
    assert grants("4-room", 70, 8_001, "single", "first")["chg"] == 0
    assert grants("4-room", 70, 4_000, "single", "no") == {"chg": 0, "ehg_max": 0, "phg": 0}


def test_income_cap():
    # cpf-guide-buying-financing.md: combined income $8,000 -> maximum instalment $2,400 (30%)
    o = loan_options(500_000, 375_000, 25, income=8_000)
    assert o["msr_cap"] == 2_400
    assert o["hdb_loan"] == 375_000  # $375k at 3.0% over 25 years is about $1,778 a month: inside the cap
    low = loan_options(500_000, 375_000, 25, income=4_000)
    assert low["hdb_loan"] == pytest.approx(loan_for_instalment(1_200, 25, 0.03))  # sized at the 3.0% floor
    assert monthly_instalment(low["hdb_loan"], 25, 0.03) == pytest.approx(1_200)
    assert low["hdb_monthly"] < 1_200  # repaid at 2.6%
    assert loan_options(500_000, 375_000, 25, income=16_001)["hdb_ok"] is False  # HDB loan income ceiling
    assert loan_options(500_000, 375_000, 25, income=8_001, household="single")["hdb_loan"] == 0


def test_bank_loan_comparison():
    o = loan_options(500_000, 375_000, 25, bank_rate=0.03)
    assert o["bank_loan"] == 375_000 and o["bank_monthly"] == pytest.approx(monthly_instalment(375_000, 25, 0.03))
    assert o["bank_cash_min"] == 25_000  # hdb-housing-loan-from-fi.md: at least 5% in cash
    assert loan_options(500_000, 375_000, 25)["bank_loan"] is None  # no rate typed, no bank figure


@pytest.mark.skipif(not Path(NODE).exists(), reason="needs Node.js")
def test_interface_costs_match_python(tmp_path):
    start = GAME.index("/* ---------- upfront cost and loans")
    code = GAME[start:GAME.index("const VTXT = ")]
    fts = ["1-room", "2-room", "4-room", "5-room", "Executive"]
    g_cases = [(ft, lease, inc, hh, first, cit, par) for ft in fts for lease in (20, 45, 70)
               for inc in (3_000, 4_500, 6_000, 9_000, 12_000, 17_000) for hh in ("family", "single")
               for first in ("first", "mixed", "no") for cit in ("sc", "spr") for par in ("no", "with", "near")]
    l_cases = [(p, loan, t, inc, hh, rate) for p in (300_000, 650_000) for loan in (0, 200_000, 480_000) for t in (0, 12.5, 25)
               for inc in (None, 3_000, 9_000, 17_000) for hh in ("", "family", "single") for rate in (None, 0.02, 0.045)]
    prices = [0, 179_999, 180_000, 360_000, 512_345, 1_000_000, 1_500_000, 3_000_000, 4_500_100]
    script = (f"{code}\nconst G={json.dumps(g_cases)}, L={json.dumps(l_cases)}, P={json.dumps(prices)};\n"
              "console.log(JSON.stringify({g:G.map(c=>grants(...c)),l:L.map(c=>loanOptions(...c)),"
              "c:[cashAtStart(460000,345000,460000,150000),cashAtStart(460000,304091,460000,150000),cashAtStart(500000,200000,90000,150000)],"
              "p:P.map(stampDuty),f:['1-room','2-room','3-room','Executive'].map(hdbFees)}));")
    (tmp_path / "costs.js").write_text(script)
    js = json.loads(subprocess.run([NODE, str(tmp_path / "costs.js")], capture_output=True, text=True, check=True).stdout)
    for case, got in zip(g_cases, js["g"]):
        assert got == grants(*case), case
    for (p, loan, t, inc, hh, rate), got in zip(l_cases, js["l"]):
        want = loan_options(p, loan, t, income=inc, household=hh, bank_rate=rate)
        assert got.keys() == want.keys()
        for k, v in want.items():
            assert got[k] == (pytest.approx(v) if isinstance(v, float) else v), (p, loan, t, inc, hh, rate, k)
    assert js["p"] == pytest.approx([stamp_duty(p) for p in prices])
    # cash at the start follows the loan shown: uncapped it is flat_money's figure, capped it grows by the cut
    assert js["c"][0] == flat_money(460_000, 60.8, [50], 150_000).cash_at_start == 0
    assert js["c"][1] == 460_000 - 304_091 - 150_000 and js["c"][2] == 500_000 - 200_000 - 90_000
    assert js["f"] == [hdb_fees(ft) for ft in ("1-room", "2-room", "3-room", "Executive")]


def test_upfront_details_stay_in_the_browser():
    """Income and grant details are never part of anything sent to the server."""
    sends = [GAME[i:GAME.index(")", i)] for i in range(len(GAME)) if GAME.startswith("RW.send(", i)]
    assert sends and not any(k in s for s in sends for k in ("S.inc", "S.hh", "S.first", "S.cit", "S.par", "bankRate"))
    facts = GAME[GAME.index("function flatFacts("):GAME.index("async function ask(")]
    assert "S.inc" not in facts and "loanOptions" not in facts and "grants(" not in facts
    assert "never sent to Runway's server or to Anthropic" in GAME
