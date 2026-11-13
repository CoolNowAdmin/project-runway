"""Convert a downloaded official page (HTML or PDF) into a corpus document.

Usage:
    python scripts/to_corpus.py <file> <slug> --url URL --title TITLE --publisher PUB

Writes data/corpus/<slug>.md with a small front-matter block that the RAG
index reads for citations. Pages that only render with JavaScript (cpf.gov.sg,
hdb.gov.sg) were copied from a browser instead and use the same format.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runway.content import html_to_text, pdf_to_text  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("slug")
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--publisher", required=True)
    args = ap.parse_args()

    data = args.file.read_bytes()
    if data[:4] == b"%PDF":
        body = pdf_to_text(data)
    else:
        body = html_to_text(data.decode("utf-8", errors="ignore"))

    header = (
        f"---\ntitle: {args.title}\npublisher: {args.publisher}\n"
        f"url: {args.url}\nretrieved: {dt.date.today().isoformat()}\n---\n\n"
    )
    out = CORPUS_DIR / f"{args.slug}.md"
    out.write_text(header + body.strip() + "\n", encoding="utf-8")
    print(f"{out.name}: {len(body.split())} words")


if __name__ == "__main__":
    main()
