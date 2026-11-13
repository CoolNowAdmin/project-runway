"""Retrieval over the fixed library of official CPF, HDB and MND documents.

Keyword search (BM25) with a few everyday synonyms, so exact terms ("Valuation Limit",
"HFE") and common paraphrases ("deposit") both find the right passage. A question in
another language is put into English first (runway.llm.LLM.search_query).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"
CHUNK_WORDS = 160
OVERLAP_WORDS = 40



@dataclass(frozen=True)
class Chunk:
    id: int
    doc: str  # file slug
    title: str
    publisher: str
    url: str
    retrieved: str
    heading: str
    text: str


def parse_doc(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    _, header, body = raw.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in header.strip().splitlines())
    return meta, body.strip()


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split on markdown headings, keeping the heading as context for each section."""
    sections, heading, buf = [], "", []
    for line in body.splitlines():
        if line.startswith("#"):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = line.lstrip("# ").strip(), []
        else:
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))
    return [(h, t) for h, t in sections if t]


def window(words: list[str], size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[list[str]]:
    if len(words) <= size:
        return [words]
    step = size - overlap
    return [words[i : i + size] for i in range(0, len(words) - overlap, step)]


def load_chunks(corpus_dir: Path | None = None) -> list[Chunk]:
    """The committed documents plus any a reviewer uploaded since the last start (runway.content)."""
    from runway.content import corpus_files

    paths = corpus_files().values() if corpus_dir is None else sorted(corpus_dir.glob("*.md"))
    chunks: list[Chunk] = []
    for path in paths:
        meta, body = parse_doc(path)
        for heading, text in split_sections(body):
            for words in window(text.split()):
                chunks.append(
                    Chunk(
                        id=len(chunks),
                        doc=path.stem,
                        title=meta["title"],
                        publisher=meta["publisher"],
                        url=meta["url"],
                        retrieved=meta["retrieved"],
                        heading=heading,
                        text=" ".join(words),
                    )
                )
    return chunks


# Everyday words buyers use -> the terms the official documents use (keyword search only).
SYNONYMS = {
    "partner": "spouse co-owner buyer",
    "wife": "spouse co-owner buyer",
    "husband": "spouse co-owner buyer",
    "younger": "youngest age",
    "older": "age",
    "cut": "pro-rated reduced",
    "reduced": "pro-rated",
    "short": "remaining lease",
    "loan": "housing loan",
    "deposit": "option fee",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# Word pairs that mean more together than apart: "how long" alone is about a letter or a lease; with "loan", its term.
PAIRS = {("long", "loan"): "repayment period"}


def expand_query(query: str) -> str:
    words = tokenize(query)
    extra = [SYNONYMS[w] for w in words if w in SYNONYMS]
    extra += [v for pair, v in PAIRS.items() if set(pair) <= set(words)]
    return " ".join([query, *extra])


class Retriever:
    mode = "keyword (BM25)"

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(f"{c.title} {c.heading} {c.text}") for c in chunks])

    def search(self, query: str, k: int = 5) -> list[Chunk]:
        scores = self.bm25.get_scores(tokenize(expand_query(query)))
        return [self.chunks[int(i)] for i in np.argsort(-scores)[:k]]


def format_context(chunks: list[Chunk]) -> str:
    """Numbered passages for the prompt; the model cites them as [1], [2], ..."""
    return "\n\n".join(
        f"[{i}] {c.title} ({c.publisher})" + (f" - {c.heading}" if c.heading else "") + f"\n{c.text}"
        for i, c in enumerate(chunks, start=1)
    )
