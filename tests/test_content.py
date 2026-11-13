"""Reviewer tools: page edits, the FAQ and uploaded Ask documents (runway/content.py via the bridge)."""

import base64
import json

import pytest

import runway.content as content
from runway.auth import hash_password
from runway.bridge import handle
from runway.rag import Retriever, load_chunks

USERS = {"reviewer": hash_password("Review-pass-1", iterations=1000)}
WORDS = " ".join(["The remaining lease decides how much CPF you can use for a resale flat."] * 5)


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch):
    """Changes go to a temp folder and never to GitHub."""
    monkeypatch.setattr(content, "RUNTIME_CORPUS", tmp_path / "corpus")
    monkeypatch.setattr(content, "RUNTIME_CONTENT", tmp_path / "content.json")
    monkeypatch.setattr(content, "CONTENT_FILE", tmp_path / "committed.json")
    monkeypatch.setattr(content, "get_setting", lambda name, default=None: default)
    return tmp_path


def send(kind, state, **payload):
    return handle({"id": "x", "type": kind, "payload": payload}, state, USERS, None, None)


def reviewer():
    return {"user": "reviewer", "role": "full"}


@pytest.mark.parametrize("kind", ["docs", "upload_doc", "save_page", "save_faq"])
def test_guests_cannot_use_reviewer_tools(kind):
    assert send(kind, {}, key="about.full", html="<p>x</p>") == {"ok": False, "error": "Log in as a reviewer first."}


def test_clean_html_keeps_formatting_and_drops_scripts():
    raw = ('<h2 class="x">Hi</h2><p onclick="steal()">a <b>b</b> <a href="javascript:alert(1)">bad</a> '
           '<a href="https://hdb.gov.sg">ok</a></p><script>alert(1)</script><img src=x onerror=alert(1)><p>&lt;tag&gt;</p>')
    out = content.clean_html(raw)
    assert out == ('<h2 class="x">Hi</h2><p>a <b>b</b> <a>bad</a> <a href="https://hdb.gov.sg" target="_blank" '
                   'rel="noopener">ok</a></p><p>&lt;tag&gt;</p>')


def test_save_page_then_restore():
    r = send("save_page", reviewer(), key="about.full", html="<h1>About</h1><p>New text</p>")
    assert r["ok"] and r["saved"] == "local" and r["content"]["pages"]["about.full"] == "<h1>About</h1><p>New text</p>"
    assert content.load_content()["pages"]["about.full"].endswith("New text</p>")
    assert send("save_page", reviewer(), key="about.full", html="")["content"]["pages"] == {}
    assert send("save_page", reviewer(), key="../secrets", html="<p>x</p>")["ok"] is False


def test_save_faq_checks_items():
    items = [{"q": "Q1?", "a": "Answer one.", "title": "T", "publisher": "HDB", "url": "javascript:alert(1)"}]
    r = send("save_faq", reviewer(), items=items)
    assert r["ok"] and r["content"]["faq"][0]["url"] == "" and r["content"]["faq"][0]["q"] == "Q1?"
    assert send("save_faq", reviewer(), items=[{"q": "", "a": "x"}])["ok"] is False
    assert send("save_faq", reviewer(), items=None)["content"]["faq"] is None


def test_upload_markdown_is_searched(runtime):
    data = base64.b64encode(f"# Lease buyback\n\n{WORDS} Zebracrossing.".encode()).decode()
    r = send("upload_doc", reviewer(), name="note.md", data=data, title="Lease note", publisher="HDB",
             url="https://www.hdb.gov.sg/x")
    assert r["ok"] and r["slug"] == "lease-note" and not r["replaced"]
    saved = (runtime / "corpus" / "lease-note.md").read_text()
    assert saved.startswith("---\ntitle: Lease note\npublisher: HDB\nurl: https://www.hdb.gov.sg/x\n")
    hits = Retriever(load_chunks()).search("zebracrossing", k=1)
    assert hits[0].doc == "lease-note"
    assert "lease-note" in {d["slug"] for d in send("docs", reviewer())["docs"]}


def test_upload_html_replaces_an_existing_doc(runtime):
    html = f"<html><nav>menu</nav><main><h1>HFE</h1><p>{WORDS}</p><script>x()</script></main></html>"
    r = send("upload_doc", reviewer(), name="page.html", data=base64.b64encode(html.encode()).decode(),
             title="HFE letter", replace="hdb-hfe-letter")
    assert r["ok"] and r["slug"] == "hdb-hfe-letter" and r["replaced"]
    body = (runtime / "corpus" / "hdb-hfe-letter.md").read_text()
    assert "# HFE" in body and "menu" not in body and "x()" not in body
    assert send("upload_doc", reviewer(), name="a.md", data=base64.b64encode(WORDS.encode()).decode(),
                replace="no-such-doc")["ok"] is False


def test_upload_rejects_empty_and_huge_files():
    assert send("upload_doc", reviewer(), name="a.txt", data=base64.b64encode(b"too short").decode())["ok"] is False
    assert send("upload_doc", reviewer(), name="a.txt", data="not base64!!")["ok"] is False
    big = base64.b64encode(b"x" * (content.MAX_UPLOAD_BYTES + 1)).decode()
    assert send("upload_doc", reviewer(), name="a.txt", data=big)["error"] == "That file is over 6 MB."


def test_commit_to_github_when_a_token_is_set(monkeypatch):
    calls = []

    class Resp:
        def __init__(self, body=b"{}"):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, *a):
            return self.body

    def urlopen(req, timeout):
        calls.append((req.get_method(), req.full_url, req.data))
        return Resp(b'{"sha": "abc"}')

    monkeypatch.setattr(content, "get_setting", lambda name, default=None: "tok" if name == "GITHUB_TOKEN" else default)
    monkeypatch.setattr(content.urllib.request, "urlopen", urlopen)
    r = send("save_page", reviewer(), key="terms", html="<p>Terms</p>")
    assert r["saved"] == "github"
    (get, url, _), (put, _, body) = calls
    assert get == "GET" and url.endswith("/repos/dansyfq/project-runway/contents/data/content.json?ref=main")
    sent = json.loads(body)
    assert put == "PUT" and sent["sha"] == "abc" and json.loads(base64.b64decode(sent["content"]))["pages"]["terms"]


def test_failed_commit_keeps_the_local_change(monkeypatch):
    def urlopen(req, timeout):
        raise OSError("no network")

    monkeypatch.setattr(content, "get_setting", lambda name, default=None: "tok" if name == "GITHUB_TOKEN" else default)
    monkeypatch.setattr(content.urllib.request, "urlopen", urlopen)
    r = send("save_page", reviewer(), key="privacy", html="<p>P</p>")
    assert r["ok"] and r["saved"] == "local" and "restarts" in r["warn"]
    assert content.load_content()["pages"]["privacy"] == "<p>P</p>"
