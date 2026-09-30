"""
CTData.org scraper for the AI hackathon — builds a corpus you can feed into an LLM.

Two layers:
  1. Site metadata (works now): crawls www.ctdata.org topic pages, extracts dataset
     names, descriptions, filter dimensions, and links -> ctdata_corpus.jsonl
  2. Data portal (CKAN): once https://data.ctdata.org is back up, pull full dataset
     metadata + download CSV resources via the standard CKAN API -> ckan_datasets.jsonl

Output is JSONL: one record per line, ready for RAG embedding / prompt stuffing.
"""

import json
import re
import time
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

OUT_DIR = Path(__file__).parent / "ctdata_corpus"
OUT_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "ctdata-hackathon-scraper/0.1 (educational)"}


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------------------
# Layer 1: scrape www.ctdata.org topic pages (site is up)
# ---------------------------------------------------------------------------

TOPIC_PAGES = [
    # Hackathon scope: education only. Add other topics back later if needed.
    "https://www.ctdata.org/education",
]


class LinkTextParser(HTMLParser):
    """Minimal parser: collects visible text and <a> href+text."""

    def __init__(self):
        super().__init__()
        self.text_chunks = []
        self.links = []
        self._cur_href = None
        self._cur_text = []
        self._skip = 0  # inside script/style

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "a":
            self._cur_href = dict(attrs).get("href")
            self._cur_text = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "a" and self._cur_href:
            label = " ".join("".join(self._cur_text).split())
            if label:
                self.links.append({"text": label, "href": self._cur_href})
            self._cur_href = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._cur_href is not None:
            self._cur_text.append(data)
        chunk = " ".join(data.split())
        if chunk:
            self.text_chunks.append(chunk)


def scrape_topic_pages():
    records = []
    for url in TOPIC_PAGES:
        try:
            html = fetch(url).decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[skip] {url}: {e}")
            continue
        p = LinkTextParser()
        p.feed(html)

        topic = url.rsplit("/", 1)[-1]
        # dataset links = links pointing at data.ctdata.org or containing dataset-ish words
        dataset_links = [
            l for l in p.links
            if "data.ctdata.org" in (l["href"] or "")
            or "edsight" in (l["href"] or "").lower()
            or re.search(r"\.(csv|xlsx|json)($|\?)", l["href"] or "", re.I)
        ]
        body_text = " ".join(p.text_chunks)
        body_text = re.sub(r"\s+", " ", body_text)[:15000]  # keep it LLM-sized

        records.append({
            "source": "ctdata.org_topic_page",
            "topic": topic,
            "url": url,
            "text": body_text,
            "dataset_links": dataset_links,
        })
        print(f"[ok] {topic}: {len(body_text)} chars, {len(dataset_links)} dataset links")
        time.sleep(1)  # be polite

    with open(OUT_DIR / "ctdata_corpus.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return records


# ---------------------------------------------------------------------------
# Layer 2: CKAN API on data.ctdata.org (currently down — run when it returns)
# ---------------------------------------------------------------------------

CKAN = "https://data.ctdata.org/api/3/action"


def scrape_ckan(queries=("education", "school", "student"), download_csvs=False):
    datasets = {}

    # full list of datasets
    try:
        listing = json.loads(fetch(f"{CKAN}/package_list"))
        names = listing["result"]
        print(f"CKAN portal lists {len(names)} datasets")
    except Exception as e:
        print(f"CKAN portal unreachable ({e}). Try again later; the site metadata "
              f"scrape in ctdata_corpus.jsonl still works.")
        return

    # topic-relevant subset via package_search
    for q in queries:
        try:
            res = json.loads(fetch(f"{CKAN}/package_search?q={q}&rows=100"))
            for pkg in res["result"]["results"]:
                datasets[pkg["name"]] = pkg
            time.sleep(1)
        except Exception as e:
            print(f"[skip] search '{q}': {e}")

    print(f"{len(datasets)} unique datasets matched queries {queries}")
    out = open(OUT_DIR / "ckan_datasets.jsonl", "w")
    for name, pkg in datasets.items():
        resources = [
            {"name": r.get("name"), "format": r.get("format"), "url": r.get("url")}
            for r in pkg.get("resources", [])
        ]
        record = {
            "source": "data.ctdata.org",
            "name": name,
            "title": pkg.get("title"),
            "description": pkg.get("notes"),
            "organization": (pkg.get("organization") or {}).get("title"),
            "tags": [t["name"] for t in pkg.get("tags", [])],
            "resources": resources,
            "url": f"https://data.ctdata.org/dataset/{name}",
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")

        if download_csvs:
            for r in resources:
                if (r.get("format") or "").upper() == "CSV" and r.get("url"):
                    try:
                        dest = OUT_DIR / "csv" / f"{name}__{Path(r['url']).name}"
                        dest.parent.mkdir(exist_ok=True)
                        dest.write_bytes(fetch(r["url"]))
                        print(f"  [csv] {dest.name}")
                        time.sleep(1)
                    except Exception as e:
                        print(f"  [csv-fail] {r['url']}: {e}")
    out.close()
    print(f"Wrote {OUT_DIR}/ckan_datasets.jsonl")


if __name__ == "__main__":
    print("=== Layer 1: scraping www.ctdata.org topic pages ===")
    scrape_topic_pages()
    print("\n=== Layer 2: CKAN data portal ===")
    scrape_ckan(download_csvs=False)
    print(f"\nDone. Corpus files are in {OUT_DIR}/")
