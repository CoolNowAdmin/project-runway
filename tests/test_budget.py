"""Budget-first search and map filters: the fit rule in Python, its JS mirror, and the town x flat type ranking."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from runway.cpf_rules import check_lease, flat_money, sale_fits

ROOT = Path(__file__).resolve().parent.parent
GAME = (ROOT / "runway_game" / "index.html").read_text(encoding="utf-8")
NODE = shutil.which("node") or str(Path.home() / ".local/bin/node")
needs_node = pytest.mark.skipif(not (shutil.which("node") or Path(NODE).exists()), reason="needs Node.js")

CALC = GAME[GAME.index("function calc(price, lease){"):GAME.index("const VTXT = ")]
FITS = GAME[GAME.index("const saleFits = "):GAME.index("const filterLabel = ")]
RANK = GAME[GAME.index("const median="):GAME.index("function findTowns(")]


def run_js(tmp_path, script):
    js = tmp_path / "budget.js"
    js.write_text(script)
    return json.loads(subprocess.run([NODE, str(js)], capture_output=True, text=True, check=True).stdout)


def test_sale_fits_is_cash_at_start_within_cash():
    m = flat_money(500_000, 70, [30, 30], 100_000)  # full CPF: loan 375k, CPF 100k, cash 25k
    assert m.cash_at_start == pytest.approx(25_000)
    assert sale_fits(500_000, 70, [30, 30], 100_000, 25_000)
    assert not sale_fits(500_000, 70, [30, 30], 100_000, 24_999)


def test_nothing_fits_without_cash_or_cpf():
    assert not any(sale_fits(p, lease, [30], 0, 0) for p in (200_000, 500_000) for lease in (15, 50, 90))


def test_cpf_not_given_means_cash_pays_what_the_loan_does_not():
    assert sale_fits(400_000, 70, [30], 0, 100_000)  # 25% down, all cash
    assert not sale_fits(400_000, 70, [30], 0, 99_999)


def test_lease_of_20_years_or_less_needs_the_whole_price_in_cash():
    for lease in (20, 15):
        assert check_lease(30, lease).cpf_share == 0
        assert not sale_fits(300_000, lease, [30], 500_000, 299_999)  # CPF cannot help
        assert sale_fits(300_000, lease, [30], 500_000, 300_000)


def test_part_cpf_sale_needs_more_cash():
    # age 40, 50 years left: CPF share (50-20)/(55-20) = 6/7, loan 75% of that
    full, part = flat_money(500_000, 70, [40], 0), flat_money(500_000, 50, [40], 0)
    assert part.cash_at_start > full.cash_at_start
    assert sale_fits(500_000, 50, [40], 0, part.cash_at_start) and not sale_fits(500_000, 50, [40], 0, full.cash_at_start)


CASES = [(p, lease, age, avg, oa, cash)
         for p in (250_000, 480_000, 820_000)
         for lease in (15, 20, 20.5, 35, 58.75, 66, 75, 94)
         for age, avg in ((25, 25), (35, 40), (64, 66))
         for oa in (None, 0, 60_000, 300_000)
         for cash in (0, 50_000, 150_000, 400_000)]


@needs_node
def test_js_sale_fits_matches_python(tmp_path):
    got = run_js(tmp_path, f"let S={{age:0,avg:0,oa:0,oaSet:false,match:null}};\n{CALC}\n{FITS}\n"
                           f"console.log(JSON.stringify({json.dumps(CASES)}.map(([p,l,a,v,oa,c])=>{{"
                           f"S.age=a;S.avg=v;S.oaSet=oa!==null;S.oa=oa||0;return saleFits({{price:p,lease:l}},c);}})));")
    assert len(got) == len(CASES) and any(got) and not all(got)
    for (p, lease, age, avg, oa, cash), fit in zip(CASES, got):
        assert fit == sale_fits(p, lease, [age, 2 * avg - age], oa or 0, cash), (p, lease, age, avg, oa, cash)


@needs_node
def test_map_filters_combine(tmp_path):
    sales = [{"ft": ft, "price": p, "lease": lease} for ft in ("3-room", "4-room") for p in (300_000, 600_000) for lease in (15, 50, 80)]
    matches = [None, {"ft": "4-room"}, {"max": 400_000}, {"cpf": "full"}, {"cpf": "part"}, {"cpf": "none"},
               {"cash": 100_000}, {"ft": "3-room", "cpf": "full", "cash": 60_000}, {"ft": "4-room", "max": 100}]
    got = run_js(tmp_path, f"let S={{age:35,avg:35,oa:50000,oaSet:true,match:null}};\n{CALC}\n{FITS}\n"
                           f"console.log(JSON.stringify({json.dumps(matches)}.map(m=>{{S.match=m;"
                           f"return {json.dumps(sales)}.filter(fits).length;}})));")

    def status(lease):
        c = check_lease(35, lease)
        return "none" if not c.cpf_allowed else "full" if c.covers_95 else "part"

    for m, n in zip(matches, got):
        m = m or {}
        want = sum(1 for s in sales
                   if s["ft"] == m.get("ft", s["ft"]) and s["price"] <= m.get("max", s["price"])
                   and status(s["lease"]) == m.get("cpf", status(s["lease"]))
                   and ("cash" not in m or sale_fits(s["price"], s["lease"], [35], 50_000, m["cash"])))
        assert n == want, m
    assert got[0] == len(sales) and got[-1] == 0  # no filters shows all; an impossible one shows none


TOWNS = ["AAA", "BBB", "CCC"]
SALES = {  # town -> (flat type, price, lease)
    "AAA": [("4-room", 450_000, 80)] * 4 + [("4-room", 900_000, 80)] * 2 + [("3-room", 300_000, 50)] * 3,
    "BBB": [("4-room", 420_000, 50)] * 5 + [("5-room", 700_000, 90)] * 3,
    "CCC": [("4-room", 400_000, 18)] * 3 + [("Executive", 950_000, 70)] * 2,  # too few Executive sales to rank
}


def rank(tmp_path, p, age=35, oa=80_000):
    sales = {t: [{"ft": ft, "price": pr, "lease": lease} for ft, pr, lease in v] for t, v in SALES.items()}
    out = run_js(tmp_path, f"let S={{age:{age},avg:{age},oa:{oa},oaSet:true,match:null}};\n{CALC}\n{FITS}\n"
                           f"const SALES={json.dumps(sales)}, TOWNS={json.dumps([{'id': t, 'name': t} for t in TOWNS])};\n"
                           f"const FTS=[...new Set(Object.values(SALES).flat().map(s=>s.ft))].sort();\n{RANK}\n"
                           f"console.log(JSON.stringify(recommend({json.dumps(p)}).map(x=>[x.t.id,x.ft,x.n,x.afford,x.good,x.score])));")
    return out


def python_counts(cash, age=35, oa=80_000):
    out = {}
    for town, rows in SALES.items():
        for ft in {r[0] for r in rows}:
            mine = [r for r in rows if r[0] == ft]
            if len(mine) < 3:
                continue
            fit = [r for r in mine if sale_fits(r[1], r[2], [age], oa, cash)]
            out[(town, ft)] = (len(mine), len(fit), sum(1 for r in fit if check_lease(age, r[2]).covers_95))
    return out


@needs_node
def test_budget_ranking_counts_fits_by_town_and_flat_type(tmp_path):
    got = rank(tmp_path, {"age": 35, "cash": 60_000, "ft": None, "towns": []})
    assert {(t, ft): (n, a, g) for t, ft, n, a, g, _ in got} == python_counts(60_000)
    assert ("CCC", "Executive") not in {(t, ft) for t, ft, *_ in got}
    fits = [(a, g) for _, _, _, a, g, _ in got]
    assert fits == sorted(fits, reverse=True)  # most sales that fit first, then most with full CPF
    assert [x[:5] for x in got[:2]] == [["AAA", "4-room", 6, 4, 4], ["AAA", "3-room", 3, 3, 0]]


@needs_node
def test_budget_ranking_with_one_flat_type_and_when_nothing_fits(tmp_path):
    got = rank(tmp_path, {"age": 35, "cash": 60_000, "ft": "4-room", "towns": []})
    assert {ft for _, ft, *_ in got} == {"4-room"} and len(got) == 3
    none = rank(tmp_path, {"age": 35, "cash": 0, "ft": None, "towns": []}, oa=0)
    assert none and all(a == 0 for _, _, _, a, _, _ in none)  # the sheet then shows its plain "none" message


@needs_node
def test_ask_upload_ranking_is_unchanged(tmp_path):
    """recommend() with a budget (the Ask page's upload) keeps its price-limit rule and its score."""
    got = rank(tmp_path, {"age": 35, "budget": 460_000, "ft": "4-room", "towns": ["CCC"]})
    for town, ft, n, afford, good, score in got:
        rows = [r for r in SALES[town] if r[0] == ft]
        assert afford == sum(1 for r in rows if r[1] <= 460_000)
        assert good == sum(1 for r in rows if r[1] <= 460_000 and r[2] > 20 and r[2] >= 60)
        assert score == pytest.approx(good / n * 60 + afford / n * 30 + (15 if town == "CCC" else 0))
    assert [t for t, *_ in got] == ["AAA", "CCC", "BBB"]


def test_budget_inputs_stay_in_the_browser():
    sends = re.findall(r"RW\.send\([^)]*\)", GAME)
    assert sends and not any("cash" in s or "match" in s for s in sends)
    assert "S.cash" not in GAME[GAME.index("RW.shown"):][:400]
    assert "Finding flats by budget and map filters" in GAME and "never put in the page address or sent to Runway's server" in GAME


def test_map_has_a_visible_filter_and_budget_entry():
    assert 'id="filterChip"' in GAME and 'id="budgetChip"' in GAME and 'id="onbBudget"' in GAME
    assert "Clear filters" in GAME and "match your filters. Clear filters or try another town." in GAME
    css = GAME[GAME.index("/* ---- budget search and map filters ---- */"):]
    assert '.chip[aria-pressed="true"]::before{content:"✓ "}' in css.split("\n/*")[0]  # selected is not colour alone
