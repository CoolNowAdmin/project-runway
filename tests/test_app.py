"""The Streamlit host and the interface file."""

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from runway.cpf_rules import cpf_share, flat_money
from runway.game_data import load_game_data, load_towns
from runway.rag import parse_doc

ROOT = Path(__file__).resolve().parent.parent
GAME = (ROOT / "runway_game" / "index.html").read_text(encoding="utf-8")
MAP = json.loads((ROOT / "data" / "game" / "map.json").read_text())
NODE = shutil.which("node") or str(Path.home() / ".local/bin/node")
needs_node = pytest.mark.skipif(not (shutil.which("node") or Path(NODE).exists()), reason="needs Node.js")
DEMO_WORDS = ("demo sign-in", "mockup", "scripted", "try it now", "live app", "runway2026")


def test_host_runs_for_a_guest():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    assert not at.exception
    assert "user" not in at.session_state


@pytest.mark.parametrize("msg", [["not", "a", "dict"], "text", {"id": ["unhashable"], "type": "ask"}])
def test_host_ignores_malformed_messages(monkeypatch, msg):
    import streamlit.components.v1 as components

    monkeypatch.setattr(components, "declare_component", lambda *a, **k: lambda **kw: msg)
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    assert not at.exception


def test_host_always_replies_even_if_handle_fails(monkeypatch):
    """No reply means the interface waits 90 s; any unexpected error must still answer the message."""
    import streamlit.components.v1 as components

    import runway.bridge

    def boom(*_):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(components, "declare_component", lambda *a, **k: lambda **kw: {"id": "m1", "type": "ask"})
    monkeypatch.setattr(runway.bridge, "handle", boom)
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    assert not at.exception
    assert at.session_state["replies"][-1] == {"id": "m1", "value": {"ok": False, "error": "Something went wrong. Try again."}}


def test_game_data_has_every_town_with_a_photo_and_credit():
    data = load_game_data()
    towns = {t["id"] for t in data["M"]["towns"]}
    assert len(towns) == 26 and set(data["PHOTOS"]) == towns
    assert all("Wikimedia Commons" in p["credit"] and p["img"].startswith("data:image/jpeg") for p in data["PHOTOS"].values())
    assert {"roads", "stops", "am"} <= set(data["F"])


def test_interface_has_no_mockup_wording_or_built_in_accounts():
    visible = re.sub(r"/\*.*?\*/", "", GAME, flags=re.S).lower()
    for word in DEMO_WORDS:
        assert word not in visible, word
    assert "USERS=" not in GAME


def test_landing_page_has_required_notice_and_entry_points():
    assert GAME.count("NOT intended for real-world usage") >= 2  # landing page (main page) and About Us
    assert 'id="scrLanding"' in GAME and 'data-go="map"' in GAME and "data-login" in GAME
    assert 'id="loginOverlay"' in GAME


@pytest.mark.skipif(not (shutil.which("node") or Path.home().joinpath(".local/bin/node").exists()),
                    reason="needs Node.js")
def test_interface_calculator_matches_python_rules(tmp_path):
    """The map's in-browser calculator must give the same numbers as runway/cpf_rules.py."""
    calc = GAME[GAME.index("function calc(price, lease){"):GAME.index("const VTXT = ")]
    landing = GAME[GAME.index("function landingShare(age, lease){"):GAME.index("window.landingShare")]
    cases = [(p, lease, age, avg) for p in (300_000, 550_000) for lease in (15, 20, 20.5, 21, 45, 58, 58.75, 65, 66.6, 74.99, 75, 95)
             for age, avg in ((21, 21), (25, 25), (28, 30), (45, 50), (70, 70), (74, 74))]
    script = (f"let S={{age:0,avg:0,oa:0,oaSet:false}};\n{calc}\n{landing}\n"
              f"const out={json.dumps(cases)}.map(([p,l,a,v])=>{{S.age=a;S.avg=v;const r=calc(p,l);"
              f"return [r.cap,r.loan,r.tenure,r.monthly,r.cashLife,landingShare(a,l)];}});\n"
              f"console.log(JSON.stringify(out));")
    js = tmp_path / "calc.js"
    js.write_text(script)
    node = shutil.which("node") or str(Path.home() / ".local/bin/node")
    results = json.loads(subprocess.run([node, str(js)], capture_output=True, text=True, check=True).stdout)
    for (price, lease, age, avg), (cap, loan, tenure, monthly, cash, share) in zip(cases, results):
        assert share == pytest.approx(cpf_share(age, lease)), ("landing", lease, age)
        m = flat_money(price, lease, [age, 2 * avg - age], 0)
        assert cap == pytest.approx(m.cpf_cap), (price, lease, age)
        assert loan == pytest.approx(m.loan_max), (price, lease, age)
        assert tenure == pytest.approx(m.tenure), (price, lease, age)
        assert monthly == pytest.approx(m.monthly, rel=1e-6), (price, lease, age)
        assert cash == pytest.approx(m.cash_on_top), (price, lease, age)


def node_json(tmp_path, script):
    js = tmp_path / "landing.js"
    js.write_text(script)
    return json.loads(subprocess.run([NODE, str(js)], capture_output=True, text=True, check=True).stdout)


def landing_verdicts(tmp_path, cases):
    code = GAME[GAME.index("function landingShare(age, lease){"):GAME.index("window.landingVerdict")]
    return node_json(tmp_path, f"const window={{}};\n{code}\n"
                               f"console.log(JSON.stringify({json.dumps(cases)}.map(([a,l])=>landingVerdict(a,l))));")


def years(n):
    return "1 year" if n == 1 else f"{n} years"


@needs_node
def test_landing_verdict_matches_python_rules(tmp_path):
    """Every age 21-85 and lease 1-99: the landing verdict gives runway/cpf_rules.py's numbers."""
    cases = [(age, lease) for age in range(21, 86) for lease in range(1, 100)]
    labels = {"none": "No CPF", "full": "Full CPF", "part": "CPF pro-rated"}
    for (age, lease), v in zip(cases, landing_verdicts(tmp_path, cases)):
        share, needed = cpf_share(age, lease), 95 - age
        status = "none" if share == 0 else "full" if share == 1 else "part"
        assert (v["status"], v["label"]) == (status, labels[status]), (age, lease)
        assert v["line"] == f"Remaining lease {years(lease)} · {years(needed)} to 95", (age, lease)
        # JS Math.round sends halves up; Python's round() sends them to the even number
        assert v["pct"] == math.floor(share * 100 + 0.5), (age, lease)
        assert v["loan"] == (0 if age >= 65 else math.floor(75 * share + 0.5)), (age, lease)
        assert v["cover"] == math.floor(min(lease / needed, 1) * 100 + 0.5), (age, lease)


@needs_node
def test_landing_verdict_sentences(tmp_path):
    no_loan = "An HDB loan is not possible from age 65, because it must be repaid by then."
    expected = {
        (52, 55): "The flat has 55 lease years left — the youngest buyer turns 95 in 43 years. With 12 years to spare, "
                  "CPF can be used up to the Valuation Limit, and the HDB loan is up to 75%.",
        (52, 44): "The flat has 44 lease years left — the youngest buyer turns 95 in 43 years. With 1 year to spare, "
                  "CPF can be used up to the Valuation Limit, and the HDB loan is up to 75%.",
        (28, 58): "The flat has 58 lease years left — the youngest buyer turns 95 in 67 years. It falls 9 years short, "
                  "so CPF use is cut to about 81% of the Valuation Limit and the HDB loan to about 61%. The rest is cash.",
        (52, 42): "The flat has 42 lease years left — the youngest buyer turns 95 in 43 years. It falls 1 year short, "
                  "so CPF use is cut to about 96% of the Valuation Limit and the HDB loan to about 72%. The rest is cash.",
        (40, 20): "With 20 years or less of lease left, CPF can't be used for this flat and a cash payment is required.",
        (70, 30): "The flat has 30 lease years left — the youngest buyer turns 95 in 25 years. With 5 years to spare, "
                  f"CPF can be used up to the Valuation Limit. {no_loan}",
        (70, 22): "The flat has 22 lease years left — the youngest buyer turns 95 in 25 years. It falls 3 years short, "
                  f"so CPF use is cut to about 40% of the Valuation Limit. {no_loan} The rest is cash.",
    }
    got = dict(zip(expected, landing_verdicts(tmp_path, list(expected))))
    for case, sentence in expected.items():
        assert got[case]["sentence"].replace("’", "'") == sentence, case
    assert got[(52, 55)]["line"] == "Remaining lease 55 years · 43 years to 95"
    assert (got[(28, 58)]["pct"], got[(28, 58)]["loan"]) == (81, 61)
    assert got[(70, 30)]["loan"] == got[(70, 22)]["loan"] == 0


@needs_node
def test_landing_answers_quote_their_documents(tmp_path):
    """The worked example on the landing page quotes the official document word for word."""
    start = GAME.index("const LANDING_QA = ")
    qa = node_json(tmp_path, GAME[start:GAME.index("/* end LANDING_QA */", start)] + "\nconsole.log(JSON.stringify(LANDING_QA));")
    assert [x["q"] for x in qa] == ["Why is your CPF usage reduced?"]
    for x in qa:
        path = ROOT / "data" / "corpus" / f"{x['doc']}.md"
        meta, _ = parse_doc(path)
        assert " ".join(x["quote"].split()) in " ".join(path.read_text(encoding="utf-8").split()), x["doc"]
        assert (x["title"], x["publisher"], x["url"]) == (meta["title"], meta["publisher"], meta["url"])
        assert x["a"].strip() and x["quote"].strip() and "[" not in x["a"] + x["quote"], x["q"]


def test_landing_calculator_dropdowns_match_the_data():
    def options(select_id):
        select = re.search(rf'<select[^>]*\bid="{select_id}"[^>]*>(.*?)</select>', GAME, re.S)
        assert select, select_id
        return re.findall(r'<option[^>]*\bvalue="([^"]*)"', select.group(1))

    towns = options("lTown")
    assert towns[0] == "" and sorted(towns[1:]) == sorted(t["id"] for t in MAP["towns"])
    assert options("lType") == ["4-room", "3-room", "5-room", "Executive"]
    assert set(options("lType")) <= {x[1] for r in MAP["recent"] for x in r["x"]}


def test_landing_town_cards_match_the_data():
    """The town cards' numbers are written into the page, so a data refresh must not leave them stale."""
    pct = {t["id"]: t["pct"] for t in MAP["towns"]}
    sales = {t["id"]: t["n"] for t in load_towns()}
    assert "−1.5% per missing year" in GAME and round(pct["TOA PAYOH"], 1) == 1.5
    assert "+0.9% per extra year" in GAME and round(pct["WOODLANDS"], 1) == 0.9
    assert "178 resales Jul–Sep 2026" in GAME and sales["SEMBAWANG"] == 178
    assert {x[0] for r in MAP["recent"] for x in r["x"]} == {"2026-07", "2026-08", "2026-09"}
    assert "≈ 11% lower price" in GAME and round((1 - (1 + pct["SEMBAWANG"] / 100) ** -10) * 100) == 11
    assert 2.5 < pct["TOA PAYOH"] / pct["YISHUN"] < 3.2  # "nearly three times"
    assert "23 more towns" in GAME and len(pct) - 3 == 23


def test_landing_look_and_copy():
    for text in ("Plus+Jakarta+Sans", "assets/punggol.jpg", "assets/toapayoh.jpg", "Less lease, less CPF:",
                 "what buyers need to know.", "Have more questions? Ask Runway.", "not from the AI"):
        assert text in GAME, text
    for text in ("IBM Plex", "--rust", "Special:FilePath", "One flat, two buyers", "ordinary way"):
        assert text not in GAME, text
    assert "7a2e1d" not in GAME.lower()


def test_landing_photos_are_local_jpegs():
    for name in ("punggol.jpg", "toapayoh.jpg"):
        assert (ROOT / "runway_game" / "assets" / name).read_bytes()[:2] == b"\xff\xd8", name
