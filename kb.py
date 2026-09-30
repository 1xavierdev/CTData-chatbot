"""Knowledge base: chunk scraped pages, embed them with LM Studio, and retrieve.

Build it after scraping:
    python kb.py            # writes data/kb.json

If LM Studio (with an embedding model loaded) is reachable, each chunk gets an
embedding vector and search is semantic. Otherwise chunks are stored without
vectors and search falls back to BM25 keyword ranking, so the demo still works.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import lmstudio

DATA_DIR = Path(__file__).parent / "data"
PAGES_FILE = DATA_DIR / "pages.json"
KB_FILE = DATA_DIR / "kb.json"

CHUNK_CHARS = 900
OVERLAP_CHARS = 150

STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i in is it me my of on or "
    "our show tell that the their there this to was what when where which who why will with "
    "you your about any data ct connecticut".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Split on line boundaries into ~size-char chunks that overlap slightly."""
    chunks, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) + 1 > size:
            chunks.append(current)
            current = current[-overlap:].split("\n", 1)[-1]  # carry over the tail, whole lines only
        current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def build_chunks(pages: list[dict]) -> list[dict]:
    chunks = []
    for page in pages:
        for i, text in enumerate(chunk_text(page["text"])):
            chunks.append({"id": f"{page['url']}#{i}", "url": page["url"], "title": page["title"], "text": text})
        # A separate "links" chunk lets the bot point people at the actual dataset pages.
        if page.get("links"):
            lines = sorted({f"- {l['label']}: {l['url']}" for l in page["links"] if len(l["label"]) > 3})
            chunks.append({
                "id": f"{page['url']}#links",
                "url": page["url"],
                "title": page["title"],
                "text": f"Links to datasets and resources on the '{page['title']}' page:\n" + "\n".join(lines),
            })
    return chunks


class KnowledgeBase:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.has_vectors = bool(chunks) and all("vector" in c for c in chunks)
        # BM25 statistics
        self.docs = [tokenize(c["title"] + " " + c["text"]) for c in chunks]
        self.avg_len = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tfs = [Counter(d) for d in self.docs]

    @classmethod
    def load(cls, path: Path = KB_FILE) -> "KnowledgeBase":
        if path.exists():
            return cls(json.loads(path.read_text()))
        if PAGES_FILE.exists():  # scraped but not built yet: keyword search only
            return cls(build_chunks(json.loads(PAGES_FILE.read_text())))
        return cls([])

    def bm25(self, query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
        terms = tokenize(query)
        scores = []
        for tf, doc in zip(self.tfs, self.docs):
            s = 0.0
            for t in terms:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * len(doc) / self.avg_len))
            scores.append(s)
        return scores

    def search(self, query: str, k: int = 4) -> list[dict]:
        if not self.chunks:
            return []
        scores = None
        if self.has_vectors:
            qvec = lmstudio.embed([query])
            if qvec:
                scores = [cosine(qvec[0], c["vector"]) for c in self.chunks]
        if scores is None:
            scores = self.bm25(query)
            if max(scores) <= 0:
                return []
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)[:k]
        return [{**{key: self.chunks[i][key] for key in ("id", "url", "title", "text")}, "score": scores[i]} for i in ranked]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def main() -> None:
    if not PAGES_FILE.exists():
        raise SystemExit("data/pages.json not found - run `python scraper.py` first.")
    chunks = build_chunks(json.loads(PAGES_FILE.read_text()))
    print(f"{len(chunks)} chunks. Embedding with LM Studio ({lmstudio.EMBED_MODEL}) ...")

    vectors = []
    for i in range(0, len(chunks), 16):
        batch = lmstudio.embed([f"{c['title']}\n{c['text']}" for c in chunks[i:i + 16]])
        if batch is None:
            print("LM Studio embeddings unavailable - saving chunks for keyword search only.")
            vectors = None
            break
        vectors.extend(batch)
    if vectors:
        for chunk, vec in zip(chunks, vectors):
            chunk["vector"] = vec

    KB_FILE.write_text(json.dumps(chunks))
    print(f"Saved {len(chunks)} chunks to {KB_FILE} ({'semantic' if vectors else 'keyword'} search)")


if __name__ == "__main__":
    main()
