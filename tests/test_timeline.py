"""More > Buying timeline: every step rests on the one document it cites."""

import re

from runway.rag import parse_doc
from tests.test_app import GAME, ROOT, needs_node, node_json


def timeline(tmp_path):
    start = GAME.index("const TIMELINE = ")
    return node_json(tmp_path, GAME[start:GAME.index("/* end TIMELINE */", start)] + "\nconsole.log(JSON.stringify(TIMELINE));")


@needs_node
def test_every_step_rests_on_its_document(tmp_path):
    steps = timeline(tmp_path)
    assert 6 <= len(steps) <= 12
    for x in steps:
        path = ROOT / "data" / "corpus" / f"{x['doc']}.md"
        meta, _ = parse_doc(path)
        assert (x["title"], x["publisher"], x["url"]) == (meta["title"], meta["publisher"], meta["url"]), x["t"]
        text = " ".join(path.read_text(encoding="utf-8").split())
        doc_numbers = {n.rstrip(",") for n in re.findall(r"\d[\d,]*", text)}
        claims = " ".join(x.get(k, "") for k in ("t", "a", "when", "lease"))
        for n in re.findall(r"\d[\d,]*", claims):  # every duration, deadline, fee and amount, with no exceptions
            assert n.rstrip(",") in doc_numbers, (x["t"], n)
        if "lease" in x:
            assert "remaining lease" in text.lower() or "the value" in text.lower(), x["t"]
    by_t = {x["t"]: x for x in steps}
    assert "21 calendar days" in by_t["Get the Option to Purchase"]["when"]
    assert "next working day" in by_t["Submit a Request for Value"]["when"] and "$120" in by_t["Submit a Request for Value"]["a"]
    assert "9 months" in by_t["Get your HFE letter"]["when"]
    assert "age 95" in by_t["Work out your budget"]["lease"]


@needs_node
def test_steps_run_from_hfe_letter_to_completion(tmp_path):
    titles = [x["t"] for x in timeline(tmp_path)]
    order = ["Get your HFE letter", "Find a flat", "Get the Option to Purchase", "Submit a Request for Value",
             "Submit the resale application", "Complete the purchase"]
    assert [t for t in titles if t in order] == order
    assert len(set(titles)) == len(titles)


def test_page_is_an_ordered_list_with_headings_under_more():
    html = GAME[GAME.index("function timelineHtml"):GAME.index("const LEGAL_DATE")]
    assert '<ol class="tl">' in html and "<h1>Buying timeline</h1>" in html and '<h2 id="tl${i}">' in html
    assert "crumbs(['more','More'],SUBNAME[s])" in GAME and "timeline:'Buying timeline'" in GAME
    assert "row('timeline','Buying timeline'," in GAME and "'timeline': 'more timeline'" in GAME
    css = GAME[GAME.index("/* ---- buying timeline ---- */"):GAME.index("/* ---- Trends")]
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", css)  # colours come from the theme tokens, so dark mode follows
