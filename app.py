"""Runway: how much lease you have left.

The interface (runway_game/index.html, built from the approved design) runs full-window as a
Streamlit component: landing page, map game, Ask and More. Visitors use it as guests; reviewers
can log in for the full About Us and How it works. Python checks logins and answers questions
from the official documents (runway/bridge.py).
Run locally with:  streamlit run app.py
"""

from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

from runway.bridge import PAGES, handle
from runway.game_data import load_game_data
from runway.llm import LLM
from runway.rag import Retriever, load_chunks

# One URL per screen. The pages are empty: the one interface below stays mounted and is told which page is open.
pages = {path: st.Page(lambda: None, title=f"{name} · Runway" if path else name, url_path=path, default=not path)
         for path, name in PAGES.items()}
pg = st.navigation(list(pages.values()), position="hidden")
HERE = Path(__file__).parent
st.set_page_config(page_title=pg.title, page_icon=str(HERE / "runway_game" / "assets" / "favicon.svg"), layout="wide",
                   initial_sidebar_state="collapsed")
pg.run()
st.markdown(
    """<style>
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], footer {display: none !important;}
    [data-testid="stMainBlockContainer"], .block-container {padding: 0 !important; max-width: 100% !important;}
    [data-testid="stAppViewContainer"], [data-testid="stMain"] {padding: 0 !important; overflow: hidden;}
    [data-testid="stVerticalBlock"] {gap: 0 !important;}
    iframe {display: block; border: 0; width: 100vw; height: 100dvh !important;}
    html, body {overflow: hidden;}
    /* Streamlit's own "Page not found" dialog for an unknown address: its box sits behind the full-window interface while
       its backdrop blocks every click. Runway shows its own notice instead (missing_page); the app uses no other dialog. */
    [data-testid="stDialog"] {display: none !important;}
    </style>""",
    unsafe_allow_html=True,
)

runway_game = components.declare_component("runway_game", path=str(HERE / "runway_game"))


@st.cache_data(show_spinner=False)
def game_data() -> dict:
    return load_game_data()


@st.cache_resource(show_spinner=False)
def llm() -> LLM:
    return LLM()


@st.cache_resource(show_spinner=False)
def retriever() -> Retriever:
    chunks, bot = load_chunks(), llm()
    if bot.available:
        try:
            return Retriever(chunks, embed=bot.embed)
        except Exception as exc:  # embeddings are an enhancement; keyword search still works
            print(f"[runway] embeddings failed, using keyword search: {type(exc).__name__}: {exc}")
    return Retriever(chunks)


def switch_page(page) -> None:
    """st.switch_page without its query-parameter reset. That reset makes the browser record the current address
    a second time, so every page change would need two presses of Back (Streamlit 1.58)."""
    try:
        from streamlit.runtime.scriptrunner import RerunData, get_script_run_ctx

        ctx = get_script_run_ctx()
        ctx.script_requests.request_rerun(RerunData(  # the same request st.switch_page makes
            query_string=ctx.query_string, page_script_hash=page._script_hash,
            cached_message_hashes=ctx.cached_message_hashes, context_info=ctx.context_info))
    except Exception:  # Streamlit internals changed: the public call still works, with the extra history entry
        st.switch_page(page)
    st.empty()  # hands control to the rerun just requested, as st.switch_page does


def configured_users() -> dict[str, str]:
    try:
        return {k.lower(): v for k, v in st.secrets["auth"]["users"].items()}
    except (KeyError, FileNotFoundError):
        return {}


state = st.session_state
replies = state.setdefault("replies", [])
handled = state.setdefault("handled", set())
me = {"user": state.get("user"), "role": state.get("role", "brief")}
# The landing page shows at once; the map data (2.5 MB) follows when the page asks for it.
data = None
if state.get("want_data") and not state.get("data_sent") and state.get("pushes", 0) < 8:
    data = game_data()
    state["pushes"] = state.get("pushes", 0) + 1  # a session needs it once; the cap stops a script asking in a loop



def missing_page() -> bool:
    """An unknown address such as /nope: Streamlit runs the home page and changes the address to /, but the first run
    still sees the address that was asked for (st.context.url). Community Cloud serves the app under /~/+/."""
    try:
        asked = [p for p in urlparse(st.context.url).path.split("/") if p not in ("", "~", "+")]
    except Exception:  # no context (tests) or Streamlit changed: no notice rather than a wrong one
        return False
    return pg.url_path == "" and bool(asked) and asked[-1] not in PAGES


msg = runway_game(me=me, data=data, replies=replies[-5:], page=pg.url_path, missing=missing_page(), key="runway", default=None)

if isinstance(msg, dict) and isinstance(msg.get("id"), str) and len(msg["id"]) <= 64 and msg["id"] not in handled:  # untrusted
    if len(handled) > 500:  # only the latest message is ever delivered again, so old ids can go
        handled.clear()
    handled.add(msg["id"])
    try:
        reply = handle(msg, state, configured_users(), llm(), retriever())
    except Exception as exc:  # always answer: without a reply the interface waits 90 s
        print(f"[runway] {str(msg.get('type'))[:40]!r} failed: {type(exc).__name__}: {exc}")
        reply = {"ok": False, "error": "Something went wrong. Try again."}
    replies.append({"id": msg["id"], "value": reply})
    del replies[:-5]  # only the last five are ever sent; in place, so logout's clear() still reaches this list
    if msg.get("type") == "nav" and reply.get("ok") and reply["page"] != pg.url_path:
        switch_page(pages[reply["page"]])
    st.rerun()
